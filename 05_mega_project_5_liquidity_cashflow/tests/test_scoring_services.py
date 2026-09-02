"""
Real test for MP5's one deployable FastAPI segment-assignment service
(Problem 4 -- hardening pass, 2026-09-02). Verified against a REAL
applicant already present in Notebook 04's own real output CSV
(`notebook_04_prepayment_segments.csv`, columns
SK_ID_CURR/PREPAYMENT_SEGMENT/TARGET + the bundle's own real
`feature_names`): the notebook's own real, already-engineered feature
vector for that applicant is fed through the service, and the returned
segment is checked to match the CSV's own real assignment exactly -- not
a mocked or fabricated expectation.

This test intentionally does NOT re-derive features from raw Kaggle CSVs
independently (Notebook 04's own internal checks already validate its
feature engineering -- see notebook_04_summary.json's n_checks_pass/
n_checks_total). It validates the one thing a serving layer must never
get wrong: given the SAME real engineered feature values the notebook
itself produced, does the persisted bundle reproduce the SAME real
segment assignment.

SKIPS CLEANLY (does not fail CI) until Notebook 04 has been re-run with
the segment-model persistence code -- as of this hardening pass, it has
not been, so no bundle/CSV exist yet.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).resolve().parent
MP5_DIR = THIS_DIR.parent
SUITE_ROOT = MP5_DIR.parent
ARTIFACTS_DIR = MP5_DIR / "decision_engine" / "artifacts"
REPORTS_DIR = MP5_DIR / "decision_engine" / "reports"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(MP5_DIR / "services"))

NB04_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_04_segment_model.joblib"
# report_builder writes CSVs under decision_engine/reports/; fall back to
# artifacts/ too in case a future run places it there instead.
NB04_CSV_CANDIDATES = [
    REPORTS_DIR / "notebook_04_prepayment_segments.csv",
    ARTIFACTS_DIR / "notebook_04_prepayment_segments.csv",
]


def _find_nb04_csv():
    for p in NB04_CSV_CANDIDATES:
        if p.exists():
            return p
    return None


skip_no_nb04 = pytest.mark.skipif(
    not (NB04_BUNDLE_PATH.exists() and _find_nb04_csv() is not None),
    reason="Notebook 04 has not been (re-)run yet with the segment-model persistence code",
)

TEST_API_KEY = "pytest-only-test-key"
AUTH = {"X-API-Key": TEST_API_KEY}


@skip_no_nb04
def test_prepayment_segment_service_matches_notebook_assignment(monkeypatch):
    import joblib

    monkeypatch.setenv("NB04_SEGMENT_MODEL_PATH", str(NB04_BUNDLE_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("prepayment_segment_assignment_service", None)
    import prepayment_segment_assignment_service as svc

    client = TestClient(svc.app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    bundle = joblib.load(NB04_BUNDLE_PATH)
    feature_names = bundle["feature_names"]

    seg_df = pd.read_csv(_find_nb04_csv())
    real_with_segment = seg_df[seg_df["PREPAYMENT_SEGMENT"] != "No Payment History"]
    if real_with_segment.empty:
        pytest.skip("No real applicant with an assigned prepayment segment found in the notebook's own output")
    real_row = real_with_segment.iloc[0]
    expected_segment = real_row["PREPAYMENT_SEGMENT"]
    payload = {f: float(real_row[f]) for f in feature_names}

    unauth = client.post("/score", json=payload)
    assert unauth.status_code == 401

    resp = client.post("/score", json=payload, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["prepayment_segment"] == expected_segment, (
        f"Service segment '{resp.json()['prepayment_segment']}' does not match notebook's own real "
        f"assignment '{expected_segment}' for real applicant {real_row['SK_ID_CURR']}"
    )
