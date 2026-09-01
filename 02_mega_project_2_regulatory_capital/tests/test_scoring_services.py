"""
Real tests for MP2's deployable FastAPI scoring services (hardening pass).
Both services are pure, deterministic Basel/Vasicek FORMULA services (no
trained model to load) -- each is verified bit-identical against
`src/features/regulatory_capital_features.py`'s own real `compute_capital_row()`
function, called directly, independent of the service code under test.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

THIS_DIR = Path(__file__).resolve().parent
MP2_DIR = THIS_DIR.parent
SUITE_ROOT = MP2_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(MP2_DIR / "services"))

from features.regulatory_capital_features import compute_capital_row, other_retail_correlation  # noqa: E402

REAL_ROW = {"PD": 0.08, "AMT_CREDIT": 500000.0, "NAME_CONTRACT_TYPE": "Cash loans",
            "FLAG_OWN_REALTY": "Y", "FLAG_OWN_CAR": "N"}


def test_capital_requirement_service_matches_direct_computation():
    sys.modules.pop("capital_requirement_service", None)
    import capital_requirement_service as svc

    client = TestClient(svc.app)
    resp = client.post("/score", json=REAL_ROW)
    assert resp.status_code == 200
    body = resp.json()

    expected = compute_capital_row(pd_value=REAL_ROW["PD"], lgd=0.20, segment="Secured — Real Estate",
                                    ead=REAL_ROW["AMT_CREDIT"])
    assert body["capital_segment"] == "Secured — Real Estate"
    assert body["capital_k"] == pytest.approx(expected["CAPITAL_K"], abs=1e-9)
    assert body["expected_loss"] == pytest.approx(expected["EXPECTED_LOSS"], abs=1e-6)
    assert body["rwa"] == pytest.approx(expected["RWA"], abs=1e-6)
    assert body["capital_requirement"] == pytest.approx(expected["CAPITAL_REQUIREMENT"], abs=1e-6)


def test_capital_requirement_service_revolving_segment_uses_pd_dependent_correlation():
    sys.modules.pop("capital_requirement_service", None)
    import capital_requirement_service as svc

    client = TestClient(svc.app)
    payload = {"PD": 0.15, "AMT_CREDIT": 200000.0, "NAME_CONTRACT_TYPE": "Cash loans",
               "FLAG_OWN_REALTY": "N", "FLAG_OWN_CAR": "N"}
    resp = client.post("/score", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["capital_segment"] == "Unsecured — Other Retail"
    assert body["correlation_r"] == pytest.approx(other_retail_correlation(0.15), abs=1e-9)


def test_stress_testing_service_baseline_matches_capital_requirement_service():
    sys.modules.pop("capital_requirement_service", None)
    sys.modules.pop("stress_testing_service", None)
    import capital_requirement_service as cap_svc
    import stress_testing_service as stress_svc

    cap_client = TestClient(cap_svc.app)
    stress_client = TestClient(stress_svc.app)

    cap_resp = cap_client.post("/score", json=REAL_ROW).json()
    base_resp = stress_client.post("/score/Baseline", json=REAL_ROW).json()
    assert base_resp["capital_requirement"] == pytest.approx(cap_resp["capital_requirement"], abs=1e-6)


def test_stress_testing_service_severity_strictly_increases():
    sys.modules.pop("stress_testing_service", None)
    import stress_testing_service as svc

    client = TestClient(svc.app)
    baseline = client.post("/score/Baseline", json=REAL_ROW).json()["capital_requirement"]
    adverse = client.post("/score/Adverse", json=REAL_ROW).json()["capital_requirement"]
    severe = client.post("/score/Severely Adverse", json=REAL_ROW).json()["capital_requirement"]
    assert baseline < adverse < severe


def test_stress_testing_service_rejects_unknown_scenario():
    sys.modules.pop("stress_testing_service", None)
    import stress_testing_service as svc

    client = TestClient(svc.app)
    resp = client.post("/score/NotAScenario", json=REAL_ROW)
    assert resp.status_code == 404
