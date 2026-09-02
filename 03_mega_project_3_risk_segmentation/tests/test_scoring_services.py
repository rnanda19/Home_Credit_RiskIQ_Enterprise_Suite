"""
Real tests for MP3's deployable FastAPI segment/tier-assignment services
(hardening pass). Each is verified against a REAL applicant already present
in that notebook's own real output CSV: this notebook's own real
already-engineered feature vector is fed through the service, and the
returned segment/tier is checked to match the CSV's own real assignment
exactly -- not a mocked or fabricated expectation.
"""
import sys
from pathlib import Path

import joblib
import polars as pl
import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).resolve().parent
MP3_DIR = THIS_DIR.parent
SUITE_ROOT = MP3_DIR.parent
ARTIFACTS_DIR = MP3_DIR / "decision_engine" / "artifacts"
FIXTURE_DIR = SUITE_ROOT / "fixture"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(MP3_DIR / "services"))

from serving.segment_assignment_common import assign_segment  # noqa: E402

NB01_SUMMARY_PATH = ARTIFACTS_DIR / "notebook_01_summary.json"
NB01_CSV = ARTIFACTS_DIR / "notebook_01_risk_tiers.csv"
NB02_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_02_segment_model.joblib"
NB02_CSV = ARTIFACTS_DIR / "notebook_02_bureau_segments.csv"
NB03_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_03_segment_model.joblib"
NB03_CSV = ARTIFACTS_DIR / "notebook_03_repayment_segments.csv"
NB04_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_04_segment_model.joblib"
NB04_CSV = ARTIFACTS_DIR / "notebook_04_utilization_segments.csv"

skip_no_nb01 = pytest.mark.skipif(not NB01_SUMMARY_PATH.exists(), reason="Notebook 01 has not been run yet")
skip_no_nb02 = pytest.mark.skipif(not (NB02_BUNDLE_PATH.exists() and NB02_CSV.exists()),
                                   reason="Notebook 02 has not been run yet (with the segment-model persistence)")
skip_no_nb03 = pytest.mark.skipif(not (NB03_BUNDLE_PATH.exists() and NB03_CSV.exists()),
                                   reason="Notebook 03 has not been run yet (with the segment-model persistence)")
skip_no_nb04 = pytest.mark.skipif(not (NB04_BUNDLE_PATH.exists() and NB04_CSV.exists()),
                                   reason="Notebook 04 has not been run yet (with the segment-model persistence)")

# 2026-09-02 hardening: every service now requires a real X-API-Key header on
# /schema and /score (never /health) -- see src/serving/auth_common.py. Only
# risk_tier_assignment_service is exercised through TestClient/HTTP in this
# file -- the segment services below call assign_segment() directly (a pure
# function, not the HTTP layer), so they are unaffected by the auth retrofit.
TEST_API_KEY = "pytest-only-test-key"
AUTH = {"X-API-Key": TEST_API_KEY}


@skip_no_nb01
def test_risk_tier_service_matches_notebook_bin_edges(monkeypatch):
    monkeypatch.setenv("NB01_SUMMARY_PATH", str(NB01_SUMMARY_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("risk_tier_assignment_service", None)
    import risk_tier_assignment_service as svc

    client = TestClient(svc.app)
    real_row = pl.read_csv(NB01_CSV).head(1).row(0, named=True)

    unauth = client.post("/score", json={"PD": real_row["PD"]})
    assert unauth.status_code == 401

    resp = client.post("/score", json={"PD": real_row["PD"]}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["risk_tier"] == real_row["RISK_TIER"]


def _cross_check_segment_service(monkeypatch, env_var, bundle_path, csv_path, module_name,
                                  segment_col, feature_module_fn, feature_module_args, response_key):
    monkeypatch.setenv(env_var, str(bundle_path))
    sys.modules.pop(module_name, None)
    __import__(module_name)

    bundle = joblib.load(bundle_path)
    feature_names = bundle["feature_names"]

    seg_df = pl.read_csv(csv_path)
    real_row = seg_df.filter(pl.col(segment_col) != seg_df[segment_col][seg_df.height - 1]).head(1)
    if real_row.height == 0:
        real_row = seg_df.head(1)
    sk_id = real_row["SK_ID_CURR"][0]
    expected_segment = real_row[segment_col][0]

    feat_df, _ = feature_module_fn(*feature_module_args)
    feat_row = feat_df.filter(pl.col("SK_ID_CURR") == sk_id)
    if feat_row.height == 0:
        pytest.skip(f"Real applicant {sk_id} not found in re-engineered features -- environment mismatch")
    payload = {f: float(feat_row[f][0]) for f in feature_names}

    got_segment, _ = assign_segment(bundle, payload)
    assert got_segment == expected_segment, (
        f"Service segment '{got_segment}' does not match notebook's own real assignment '{expected_segment}' "
        f"for real applicant {sk_id}"
    )


@skip_no_nb02
def test_bureau_segment_service_matches_notebook_assignment(monkeypatch):
    from features.risk_segmentation_features import engineer_bureau_behavior_features

    nb01 = pl.read_csv(NB01_CSV)
    bureau = pl.read_csv(FIXTURE_DIR / "bureau.csv")
    bureau_balance = pl.read_csv(FIXTURE_DIR / "bureau_balance.csv")

    _cross_check_segment_service(
        monkeypatch, "NB02_SEGMENT_MODEL_PATH", NB02_BUNDLE_PATH, NB02_CSV,
        "bureau_segment_assignment_service", "BUREAU_SEGMENT",
        engineer_bureau_behavior_features, (nb01.select("SK_ID_CURR"), bureau, bureau_balance),
        "bureau_segment",
    )


@skip_no_nb03
def test_repayment_segment_service_matches_notebook_assignment(monkeypatch):
    from features.risk_segmentation_features import engineer_repayment_behavior_features

    nb01 = pl.read_csv(NB01_CSV)
    installments = pl.read_csv(FIXTURE_DIR / "installments_payments.csv")
    pos_cash = pl.read_csv(FIXTURE_DIR / "POS_CASH_balance.csv")

    _cross_check_segment_service(
        monkeypatch, "NB03_SEGMENT_MODEL_PATH", NB03_BUNDLE_PATH, NB03_CSV,
        "repayment_segment_assignment_service", "REPAYMENT_SEGMENT",
        lambda ids, i, p: engineer_repayment_behavior_features(ids, i, p)[:2],
        (nb01.select("SK_ID_CURR"), installments, pos_cash),
        "repayment_segment",
    )


@skip_no_nb04
def test_utilization_segment_service_matches_notebook_assignment(monkeypatch):
    from features.risk_segmentation_features import engineer_revolving_credit_utilization_features

    nb01 = pl.read_csv(NB01_CSV)
    credit_card = pl.read_csv(FIXTURE_DIR / "credit_card_balance.csv")

    _cross_check_segment_service(
        monkeypatch, "NB04_SEGMENT_MODEL_PATH", NB04_BUNDLE_PATH, NB04_CSV,
        "utilization_segment_assignment_service", "UTILIZATION_SEGMENT",
        lambda ids, c: engineer_revolving_credit_utilization_features(ids, c)[:2],
        (nb01.select("SK_ID_CURR"), credit_card),
        "utilization_segment",
    )
