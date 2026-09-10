"""
Real end-to-end integration tests for both of MP2's deployable services
(capital_requirement_service.py, stress_testing_service.py). Added
2026-09-10, closing this Mega Project's share of the suite-wide disclosed
gap: "No end-to-end integration test suite exists -- every existing
service test uses in-process `TestClient`, which never exercises the real
`uvicorn` startup path, real networking, or real process lifecycle."

Every assertion below is a real HTTP round trip (via `requests`, a real
socket) against a real `uvicorn` subprocess running the exact real service
module this suite documents and ships in its Docker image -- not FastAPI's
in-process `TestClient`. Neither MP2 service needs a model bundle at all
(both are real, closed-form Basel formula services -- see each service's
own module docstring), so these fixtures need no `joblib.dump()`.

Every expected numeric value below was independently recomputed by hand
(scipy.stats.norm, the exact same Vasicek/ASRF formula
`regulatory_capital_features.basel_retail_capital_k()` implements) before
being written into this file -- not copied from a service response and
asserted back at itself.

These tests do NOT replace `tests/test_scoring_services.py` (bit-identical
output verification against an independent reference computation) -- they
add the one thing that cannot provide: proof each real deployed process
actually starts and serves real traffic end to end.
"""

import sys
from pathlib import Path

import pytest
import requests

THIS_DIR = Path(__file__).resolve().parent
MP2_DIR = THIS_DIR.parent
SUITE_ROOT = MP2_DIR.parent
SERVICE_DIR = MP2_DIR / "services"

sys.path.insert(0, str(SUITE_ROOT / "src"))

from testing.e2e_process_harness import run_service_subprocess  # noqa: E402

PORT_CAPITAL = 8905
PORT_STRESS = 8906
TEST_API_KEY = "e2e-pytest-only-test-key"
TEST_JWT_SECRET = "e2e-pytest-only-test-jwt-secret"

# Real applicant fixture used by both services below: Cash loans, owns real
# estate -> "Secured — Real Estate" segment (LGD 0.20, R fixed 0.15, per
# SEGMENT_DEFINITIONS). PD and AMT_CREDIT are deliberately round numbers so
# the independently-recomputed reference values below stay easy to audit.
REAL_ESTATE_APPLICANT = {
    "PD": 0.05,
    "AMT_CREDIT": 500000.0,
    "NAME_CONTRACT_TYPE": "Cash loans",
    "FLAG_OWN_REALTY": "Y",
    "FLAG_OWN_CAR": "N",
}

# ---------------------------------------------------------------------------
# Problem 1 -- Expected Loss & Capital Requirement (capital_requirement_service.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_capital():
    """Real subprocess-launched instance of the capital-requirement service.
    No model bundle -- real, deterministic Basel formula only, see module
    docstring."""
    env = {"API_KEY": TEST_API_KEY, "JWT_SECRET_KEY": TEST_JWT_SECRET}
    with run_service_subprocess(
        module_name="capital_requirement_service",
        service_dir=SERVICE_DIR,
        port=PORT_CAPITAL,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_capital_health_is_open_with_no_model_dependency(live_service_capital):
    resp = requests.get(f"{live_service_capital}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "no trained model" in body["note"]


def test_capital_schema_and_score_reject_missing_auth_over_real_http(
    live_service_capital,
):
    resp = requests.get(f"{live_service_capital}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_capital}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_capital_schema_lists_the_real_4_segment_table(live_service_capital):
    resp = requests.get(
        f"{live_service_capital}/schema",
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["segment_order"]) == {
        "Secured — Real Estate",
        "Secured — Other (Vehicle/Goods)",
        "Unsecured — Other Retail",
        "Revolving (QRRE)",
    }


def test_capital_real_score_call_matches_the_independently_recomputed_basel_k(
    live_service_capital,
):
    resp = requests.post(
        f"{live_service_capital}/score",
        json=REAL_ESTATE_APPLICANT,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["capital_segment"] == "Secured — Real Estate"
    assert body["lgd_assumed"] == pytest.approx(0.20)
    assert body["correlation_r"] == pytest.approx(0.15)
    # Real values hand-recomputed via scipy.stats.norm against the exact
    # same Vasicek/ASRF formula -- see module docstring.
    assert body["capital_k"] == pytest.approx(0.05270118158735763, rel=1e-9)
    assert body["expected_loss"] == pytest.approx(5000.0, rel=1e-9)
    assert body["rwa"] == pytest.approx(329382.38492098515, rel=1e-9)
    assert body["capital_requirement"] == pytest.approx(26350.590793678813, rel=1e-9)


# ---------------------------------------------------------------------------
# Problem 4 -- Macro Stress Testing (stress_testing_service.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_stress():
    """Real subprocess-launched instance of the macro-stress-testing
    service. No model bundle -- real, deterministic Basel formula only,
    same as the capital-requirement service above."""
    env = {"API_KEY": TEST_API_KEY, "JWT_SECRET_KEY": TEST_JWT_SECRET}
    with run_service_subprocess(
        module_name="stress_testing_service",
        service_dir=SERVICE_DIR,
        port=PORT_STRESS,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_stress_health_lists_the_real_3_scenarios(live_service_stress):
    resp = requests.get(f"{live_service_stress}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body["scenarios"]) == {"Baseline", "Adverse", "Severely Adverse"}


def test_stress_schema_and_score_reject_missing_auth_over_real_http(
    live_service_stress,
):
    resp = requests.get(f"{live_service_stress}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_stress}/score/Baseline", json={}, timeout=5)
    assert resp.status_code == 401


def test_stress_unknown_scenario_returns_a_real_404(live_service_stress):
    resp = requests.post(
        f"{live_service_stress}/score/Not-A-Real-Scenario",
        json=REAL_ESTATE_APPLICANT,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 404


def test_stress_baseline_scenario_leaves_pd_unstressed(live_service_stress):
    resp = requests.post(
        f"{live_service_stress}/score/Baseline",
        json=REAL_ESTATE_APPLICANT,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stressed_pd"] == pytest.approx(REAL_ESTATE_APPLICANT["PD"])
    assert body["z_shock"] == pytest.approx(0.0)


def test_stress_adverse_scenario_matches_the_independently_recomputed_stressed_pd(
    live_service_stress,
):
    resp = requests.post(
        f"{live_service_stress}/score/Adverse",
        json=REAL_ESTATE_APPLICANT,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    # Real values hand-recomputed via scipy.stats.norm against the exact
    # same single-factor Vasicek conditional-PD-given-Z formula -- see
    # module docstring.
    assert body["stressed_pd"] == pytest.approx(0.13717537853449902, rel=1e-9)
    assert body["stressed_lgd"] == pytest.approx(0.20, rel=1e-9)
    assert body["capital_k"] == pytest.approx(0.08152428367093507, rel=1e-9)
    assert body["expected_loss"] == pytest.approx(13717.537853449903, rel=1e-9)
    assert body["rwa"] == pytest.approx(509526.77294334426, rel=1e-9)
    assert body["capital_requirement"] == pytest.approx(40762.14183546754, rel=1e-9)
