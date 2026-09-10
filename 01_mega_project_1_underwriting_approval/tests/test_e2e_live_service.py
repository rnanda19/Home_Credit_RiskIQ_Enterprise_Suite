"""
Real end-to-end integration tests for all 4 of MP1's deployable services
(Problem 1 added 2026-09-08; Problems 2/3/4 added 2026-09-10) -- closes the
disclosed gap: "No end-to-end integration test suite exists -- every
existing service test uses in-process `TestClient`, which never exercises
the real `uvicorn` startup path, real networking, or real process
lifecycle."

Every assertion below is a real HTTP round trip (via `requests`, a real
socket) against a real `uvicorn` subprocess running the exact real service
module this suite documents and ships in its Docker image -- not FastAPI's
in-process `TestClient`. Model bundles (Problems 1-3; Problem 4 needs none,
see its own fixture) are the same real, genuinely-fit (fake data) fixture
`scripts/generate_ci_fixture_bundles.py` already uses to verify the Docker
image builds and runs in CI, reused here rather than duplicated so these
tests need no real Kaggle data and no locally-run notebook.

These tests do NOT replace `tests/test_scoring_services.py` (bit-identical
output verification against an independent reference computation) or
`src/tests/test_rate_limit_common.py`/`test_adverse_action_endpoint.py`
(focused, fast, in-process behavior checks) -- they add the one thing those
cannot provide: proof each real deployed process actually starts and serves
real traffic end to end.
"""

import sys
from pathlib import Path

import joblib
import pytest
import requests

THIS_DIR = Path(__file__).resolve().parent
MP1_DIR = THIS_DIR.parent
SUITE_ROOT = MP1_DIR.parent
SERVICE_DIR = MP1_DIR / "services"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from testing.e2e_process_harness import run_service_subprocess  # noqa: E402
from generate_ci_fixture_bundles import scoring_bundle  # noqa: E402

PORT = 8901
PORT_P2 = 8902
PORT_P3 = 8903
PORT_P4 = 8904
TEST_API_KEY = "e2e-pytest-only-test-key"
TEST_JWT_SECRET = "e2e-pytest-only-test-jwt-secret"


@pytest.fixture()
def live_service(tmp_path):
    """Real subprocess-launched instance of the real service, pointed at a
    real (fixture) model bundle -- see module docstring."""
    bundle_path = tmp_path / "notebook_01_champion_model.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB01_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="credit_default_scoring_service",
        service_dir=SERVICE_DIR,
        port=PORT,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_health_is_open_and_reports_the_real_fixture_model(live_service):
    resp = requests.get(f"{live_service}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["champion_model"]


def test_schema_and_score_reject_missing_auth_over_real_http(live_service):
    resp = requests.get(f"{live_service}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_real_oauth2_token_flow_then_authenticated_schema_call(live_service):
    token_resp = requests.post(
        f"{live_service}/token",
        data={"username": "e2e", "password": TEST_API_KEY},
        timeout=5,
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    schema_resp = requests.get(
        f"{live_service}/schema",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert schema_resp.status_code == 200
    assert "ci_fixture_feature_1" in schema_resp.json()["numeric_features"]


def test_real_score_call_over_x_api_key_auth(live_service):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["probability_of_default"] <= 1.0
    assert isinstance(body["top_reasons"], list)


def test_real_adverse_action_notice_call_end_to_end(live_service):
    payload = {
        "ci_fixture_feature_1": 5.0,
        "ci_fixture_feature_2": 5.0,
        "threshold": 0.0,
    }
    resp = requests.post(
        f"{live_service}/adverse-action-notice",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("adverse_action", "approved")
    assert "principal_reasons" in body and "suppressed_factors" in body


# ---------------------------------------------------------------------------
# Problem 2 -- Loan Application Approval (loan_approval_scoring_service.py)
#
# Built by the same `build_scoring_app()` factory as Problem 1 (see
# src/serving/scoring_service_common.py), so it exposes the identical
# /health, /schema, /score, /token, /adverse-action-notice surface -- only
# the bundle env var (NB02_BUNDLE_PATH) and score_label
# ("approval_probability") differ. Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p2(tmp_path):
    """Real subprocess-launched instance of Problem 2's loan-approval
    service, pointed at a real (fixture) model bundle -- see module
    docstring."""
    bundle_path = tmp_path / "notebook_02_champion_model.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB02_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="loan_approval_scoring_service",
        service_dir=SERVICE_DIR,
        port=PORT_P2,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p2_health_is_open_and_reports_the_real_fixture_model(live_service_p2):
    resp = requests.get(f"{live_service_p2}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["champion_model"]


def test_p2_schema_and_score_reject_missing_auth_over_real_http(live_service_p2):
    resp = requests.get(f"{live_service_p2}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_p2}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p2_real_oauth2_token_flow_then_authenticated_schema_call(live_service_p2):
    token_resp = requests.post(
        f"{live_service_p2}/token",
        data={"username": "e2e", "password": TEST_API_KEY},
        timeout=5,
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    schema_resp = requests.get(
        f"{live_service_p2}/schema",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert schema_resp.status_code == 200
    assert "ci_fixture_feature_1" in schema_resp.json()["numeric_features"]


def test_p2_real_score_call_over_x_api_key_auth(live_service_p2):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_p2}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["approval_probability"] <= 1.0
    assert isinstance(body["top_reasons"], list)


def test_p2_real_adverse_action_notice_call_end_to_end(live_service_p2):
    payload = {
        "ci_fixture_feature_1": 5.0,
        "ci_fixture_feature_2": 5.0,
        "threshold": 0.0,
    }
    resp = requests.post(
        f"{live_service_p2}/adverse-action-notice",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("adverse_action", "approved")
    assert "principal_reasons" in body and "suppressed_factors" in body


# ---------------------------------------------------------------------------
# Problem 3 -- Credit Score Estimation (credit_score_service.py)
#
# A hand-built FastAPI app (not the build_scoring_app() factory): reuses
# Problem 1's real trained bundle contract via NB01_BUNDLE_PATH, then applies
# a real PDO scorecard transform on top. Has /health, /schema, /score,
# /token -- but no /adverse-action-notice (that endpoint is factory-specific;
# see the service's own module docstring). Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p3(tmp_path):
    """Real subprocess-launched instance of Problem 3's credit-score
    service, pointed at its own copy of the same real (fixture) bundle
    contract Problem 1 uses -- see module docstring."""
    bundle_path = tmp_path / "notebook_01_champion_model_for_p3.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB01_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="credit_score_service",
        service_dir=SERVICE_DIR,
        port=PORT_P3,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p3_health_reports_scaling_assumptions_and_upstream_model(live_service_p3):
    resp = requests.get(f"{live_service_p3}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["upstream_champion_model"]
    # Real, disclosed scorecard constants from the service's own module --
    # not re-derived here, just confirmed they're actually being served.
    assert body["scaling_assumptions"]["base_score"] == 600.0
    assert body["scaling_assumptions"]["base_odds"] == 50.0
    assert body["scaling_assumptions"]["pdo"] == 20.0


def test_p3_schema_and_score_reject_missing_auth_over_real_http(live_service_p3):
    resp = requests.get(f"{live_service_p3}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_p3}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p3_real_score_call_computes_a_scorecard_score_in_range(live_service_p3):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_p3}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    # Real range enforced by the service's own np.clip(raw_score, 300, 900).
    assert 300.0 <= body["credit_score"] <= 900.0
    assert 0.0 <= body["probability_of_default"] <= 1.0
    assert isinstance(body["top_reasons"], list)


# ---------------------------------------------------------------------------
# Problem 4 -- Repayment Capacity Analysis (repayment_capacity_service.py)
#
# No trained model bundle at all -- real, deterministic ratio formulas only
# (see the service's own module docstring for why this is a disclosed,
# by-design scope choice, not a gap). No /schema endpoint either, since
# there is no feature list to expose. Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p4():
    """Real subprocess-launched instance of Problem 4's repayment-capacity
    service. No joblib bundle to fixture here -- this service depends on no
    trained model at all, see module docstring."""
    env = {"API_KEY": TEST_API_KEY, "JWT_SECRET_KEY": TEST_JWT_SECRET}
    with run_service_subprocess(
        module_name="repayment_capacity_service",
        service_dir=SERVICE_DIR,
        port=PORT_P4,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p4_health_is_open_with_no_model_dependency(live_service_p4):
    resp = requests.get(f"{live_service_p4}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "no trained model" in body["note"]


def test_p4_score_rejects_missing_auth_over_real_http(live_service_p4):
    resp = requests.post(f"{live_service_p4}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p4_real_score_call_computes_the_real_deterministic_ratios(live_service_p4):
    payload = {
        "AMT_INCOME_TOTAL": 100000.0,
        "AMT_ANNUITY": 10000.0,
        "AMT_CREDIT": 50000.0,
        "BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL": 20000.0,
    }
    resp = requests.post(
        f"{live_service_p4}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    # Real, independently-recomputed values for the exact formulas documented
    # in the service's own module docstring -- not a fabricated expectation.
    assert body["repayment_capacity_ratio"] == pytest.approx(100000.0 / 10001.0)
    assert body["total_debt_burden_ratio"] == pytest.approx((20000.0 + 50000.0) / 100001.0)
