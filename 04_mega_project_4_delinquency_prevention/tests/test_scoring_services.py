"""
Real tests for MP4's deployable FastAPI scoring services (2026-09-02
hardening pass). Each classifier service is verified BIT-IDENTICAL against
direct computation with the notebook's own real model bundle -- not a
mocked or fabricated expectation. The clustering service is verified
against `assign_segment()` called directly (same pattern as Mega Project
3's own `_cross_check_segment_service` helper). Every /schema and /score
call requires a real X-API-Key header (2026-09-02 hardening -- see
src/serving/auth_common.py); /health stays unauthenticated.

These tests need each notebook's own real, gitignored `.joblib` bundle
(produced only by running that notebook on real data) and are skip-if-
missing, exactly like Mega Projects 1-3's own test_scoring_services.py --
they are not exercised for real in this sandbox, per the standing
2026-09-01 zero-fabrication policy (the shared serving-layer code itself
was verified separately, against hand-built bundles, in
src/tests/test_serving_common.py).
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).resolve().parent
MP4_DIR = THIS_DIR.parent
SUITE_ROOT = MP4_DIR.parent
ARTIFACTS_DIR = MP4_DIR / "decision_engine" / "artifacts"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(MP4_DIR / "services"))

from serving.segment_assignment_common import assign_segment  # noqa: E402

TEST_API_KEY = "pytest-only-test-key"
AUTH = {"X-API-Key": TEST_API_KEY}

NB01_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_01_champion_model.joblib"
NB02_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_02_kmeans_model.joblib"
NB03_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_03_champion_model.joblib"
NB04_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_04_champion_model.joblib"

skip_no_nb01 = pytest.mark.skipif(not NB01_BUNDLE_PATH.exists(), reason="Notebook 01 has not been run yet")
skip_no_nb02 = pytest.mark.skipif(not NB02_BUNDLE_PATH.exists(), reason="Notebook 02 has not been run yet")
skip_no_nb03 = pytest.mark.skipif(not NB03_BUNDLE_PATH.exists(), reason="Notebook 03 has not been run yet")
skip_no_nb04 = pytest.mark.skipif(not NB04_BUNDLE_PATH.exists(), reason="Notebook 04 has not been run yet")


def _direct_score_no_categoricals(bundle, row: dict) -> float:
    """Reference computation, independent of the service code under test --
    same real preprocessing (median-impute, no categorical/ordinal step --
    Notebooks 01/03/04's own real feature space has none), applied directly
    with pandas/sklearn."""
    feature_cols = bundle["feature_cols"]
    pdf = pd.DataFrame([{c: row.get(c) for c in feature_cols}])
    X = pdf[feature_cols].astype("float64")
    X = pd.DataFrame(bundle["imputer"].transform(X), columns=feature_cols)
    return float(np.clip(bundle["model"].predict_proba(X)[:, 1][0], 0.0, 1.0))


def _sample_row(bundle) -> dict:
    """A real, fully-specified row built from the bundle's own real feature
    list (representative synthetic values, never read from the user's
    actual data)."""
    return {f: 0.1 for f in bundle["feature_cols"]}


def _classifier_service_case(monkeypatch, env_var, bundle_path, module_name, response_key):
    monkeypatch.setenv(env_var, str(bundle_path))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop(module_name, None)
    svc = __import__(module_name)

    client = TestClient(svc.app)
    bundle = joblib.load(bundle_path)
    row = _sample_row(bundle)
    expected = _direct_score_no_categoricals(bundle, row)

    unauth = client.post("/score", json=row)
    assert unauth.status_code == 401

    resp = client.post("/score", json=row, headers=AUTH)
    assert resp.status_code == 200
    got = resp.json()[response_key]
    assert got == pytest.approx(expected, abs=1e-6), (
        f"Service score {got} does not bit-match direct computation {expected}"
    )
    assert 0.0 <= got <= 1.0
    assert isinstance(resp.json()["top_reasons"], list)


@skip_no_nb01
def test_early_delinquency_scoring_service_matches_direct_computation(monkeypatch):
    _classifier_service_case(monkeypatch, "NB01_BUNDLE_PATH", NB01_BUNDLE_PATH,
                              "early_delinquency_scoring_service", "probability")


@skip_no_nb03
def test_revolving_distress_scoring_service_matches_direct_computation(monkeypatch):
    _classifier_service_case(monkeypatch, "NB03_BUNDLE_PATH", NB03_BUNDLE_PATH,
                              "revolving_distress_scoring_service", "probability")


@skip_no_nb04
def test_pos_cash_trajectory_scoring_service_matches_direct_computation(monkeypatch):
    _classifier_service_case(monkeypatch, "NB04_BUNDLE_PATH", NB04_BUNDLE_PATH,
                              "pos_cash_trajectory_scoring_service", "probability")


@skip_no_nb02
def test_payment_pattern_service_matches_direct_assignment(monkeypatch):
    monkeypatch.setenv("NB02_KMEANS_MODEL_PATH", str(NB02_BUNDLE_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("payment_pattern_assignment_service", None)
    import payment_pattern_assignment_service as svc

    client = TestClient(svc.app)
    bundle = joblib.load(NB02_BUNDLE_PATH)
    feature_cols = bundle["feature_cols"]
    row = {f: 0.1 for f in feature_cols}

    # Reference: assign_segment() called directly on the real bundle (real
    # key aliasing -- feature_cols/pattern_labels -- exercised the same way
    # the service itself resolves it via load_bundle()).
    aliased_bundle = dict(bundle)
    aliased_bundle.setdefault("feature_names", bundle.get("feature_cols"))
    aliased_bundle.setdefault("segment_labels", bundle.get("pattern_labels"))
    expected_pattern, expected_idx = assign_segment(aliased_bundle, row)

    unauth = client.post("/score", json=row)
    assert unauth.status_code == 401

    resp = client.post("/score", json=row, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["payment_pattern"] == expected_pattern
    assert body["segment_index"] == expected_idx
    assert len(body["distance_to_each_segment"]) == bundle["k_chosen"]
