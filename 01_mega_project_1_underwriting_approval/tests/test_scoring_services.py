"""
Real tests for MP1's deployable FastAPI scoring services (task #24 hardening
pass). Each service is verified BIT-IDENTICAL against the notebook's own
direct computation on a real sample row from that notebook's own model bundle
-- not a mocked or fabricated expectation.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).resolve().parent
MP1_DIR = THIS_DIR.parent
SUITE_ROOT = MP1_DIR.parent
ARTIFACTS_DIR = MP1_DIR / "decision_engine" / "artifacts"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(MP1_DIR / "services"))

# 2026-09-02 hardening: every service now requires a real X-API-Key header on
# /schema and /score (never /health) -- see src/serving/auth_common.py. Every
# test below that calls /schema or /score sets this same real env var via
# monkeypatch and sends this same header.
TEST_API_KEY = "pytest-only-test-key"
AUTH = {"X-API-Key": TEST_API_KEY}


def _direct_score(bundle, row: dict) -> float:
    """Reference computation, independent of the service code under test --
    same preprocessing pipeline, applied directly with pandas/sklearn."""
    numeric_features = bundle["numeric_features"]
    categorical_features = bundle["categorical_features"]
    feature_cols = bundle["feature_cols"]
    pdf = pd.DataFrame([{c: row.get(c) for c in feature_cols}])
    for c in categorical_features:
        pdf[c] = pdf[c].astype(object).fillna("Missing").astype(str)
    for c in numeric_features:
        pdf[c] = pdf[c].astype("float32")
    X = pdf[feature_cols].copy()
    if categorical_features:
        X[categorical_features] = bundle["ordinal_encoder"].transform(pdf[categorical_features].astype(str))
    X[numeric_features] = bundle["imputer"].transform(pdf[numeric_features])
    return float(np.clip(bundle["model"].predict_proba(X)[:, 1][0], 0.0, 1.0))


def _sample_row(bundle) -> dict:
    """A real, fully-specified row built from the bundle's own real feature list
    (representative synthetic values, never read from the user's actual data)."""
    row = {}
    for f in bundle["numeric_features"]:
        row[f] = 50000.0
    for f in bundle["categorical_features"]:
        row[f] = "Missing"
    return row


NB01_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_01_champion_model.joblib"
NB02_BUNDLE_PATH = ARTIFACTS_DIR / "notebook_02_champion_model.joblib"
skip_no_nb01 = pytest.mark.skipif(not NB01_BUNDLE_PATH.exists(), reason="Notebook 01 has not been run yet")
skip_no_nb02 = pytest.mark.skipif(not NB02_BUNDLE_PATH.exists(), reason="Notebook 02 has not been run yet")


@skip_no_nb01
def test_credit_default_scoring_service_matches_direct_computation(monkeypatch):
    monkeypatch.setenv("NB01_BUNDLE_PATH", str(NB01_BUNDLE_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("credit_default_scoring_service", None)
    import credit_default_scoring_service as svc

    client = TestClient(svc.app)
    bundle = joblib.load(NB01_BUNDLE_PATH)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["champion_model"] == bundle["champion_name"]

    row = _sample_row(bundle)
    expected = _direct_score(bundle, row)

    # No key -> 401 (real auth retrofit, 2026-09-02 hardening)
    unauth = client.post("/score", json=row)
    assert unauth.status_code == 401

    resp = client.post("/score", json=row, headers=AUTH)
    assert resp.status_code == 200
    got = resp.json()["probability_of_default"]
    assert got == pytest.approx(expected, abs=1e-6), (
        f"Service score {got} does not bit-match direct computation {expected}"
    )
    assert 0.0 <= got <= 1.0
    assert isinstance(resp.json()["top_reasons"], list)


@skip_no_nb02
def test_loan_approval_scoring_service_matches_direct_computation(monkeypatch):
    monkeypatch.setenv("NB02_BUNDLE_PATH", str(NB02_BUNDLE_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("loan_approval_scoring_service", None)
    import loan_approval_scoring_service as svc

    client = TestClient(svc.app)
    bundle = joblib.load(NB02_BUNDLE_PATH)
    row = _sample_row(bundle)
    expected = _direct_score(bundle, row)

    unauth = client.post("/score", json=row)
    assert unauth.status_code == 401

    resp = client.post("/score", json=row, headers=AUTH)
    assert resp.status_code == 200
    got = resp.json()["approval_probability"]
    assert got == pytest.approx(expected, abs=1e-6)
    assert 0.0 <= got <= 1.0
    assert isinstance(resp.json()["top_reasons"], list)


@skip_no_nb01
def test_credit_score_service_pdo_scaling_matches_manual_computation(monkeypatch):
    monkeypatch.setenv("NB01_BUNDLE_PATH", str(NB01_BUNDLE_PATH))
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("credit_score_service", None)
    import credit_score_service as svc

    client = TestClient(svc.app)
    bundle = joblib.load(NB01_BUNDLE_PATH)
    row = _sample_row(bundle)
    pd_direct = _direct_score(bundle, row)
    pd_clipped = float(np.clip(pd_direct, 1e-6, 1 - 1e-6))
    odds = (1 - pd_clipped) / pd_clipped
    factor = 20.0 / np.log(2)
    offset = 600.0 - factor * np.log(50.0)
    expected_score = float(np.clip(offset + factor * np.log(odds), 300, 900))

    unauth = client.post("/score", json=row)
    assert unauth.status_code == 401

    resp = client.post("/score", json=row, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["credit_score"] == pytest.approx(expected_score, abs=1e-4)
    assert 300 <= body["credit_score"] <= 900
    assert body["scaling_assumptions"]["base_score"] == 600.0
    assert body["scaling_assumptions"]["pdo"] == 20.0


def test_repayment_capacity_service_formulas(monkeypatch):
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("repayment_capacity_service", None)
    import repayment_capacity_service as svc

    client = TestClient(svc.app)
    payload = {"AMT_INCOME_TOTAL": 200000.0, "AMT_ANNUITY": 24000.0, "AMT_CREDIT": 500000.0,
               "BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL": 100000.0}
    unauth = client.post("/score", json=payload)
    assert unauth.status_code == 401

    resp = client.post("/score", json=payload, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    expected_capacity = 200000.0 / (24000.0 + 1.0)
    expected_burden = (100000.0 + 500000.0) / (200000.0 + 1.0)
    assert body["repayment_capacity_ratio"] == pytest.approx(expected_capacity, abs=1e-9)
    assert body["total_debt_burden_ratio"] == pytest.approx(expected_burden, abs=1e-9)


def test_repayment_capacity_service_handles_missing_annuity_gracefully(monkeypatch):
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
    sys.modules.pop("repayment_capacity_service", None)
    import repayment_capacity_service as svc

    client = TestClient(svc.app)
    resp = client.post("/score", json={"AMT_INCOME_TOTAL": 100000.0}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["repayment_capacity_ratio"] is None
    assert body["total_debt_burden_ratio"] is None
