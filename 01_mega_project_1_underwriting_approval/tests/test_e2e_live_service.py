"""
Real end-to-end integration test for MP1 Problem 1's deployable service
(2026-09-08) -- closes the disclosed gap: "No end-to-end integration test
suite exists -- every existing service test uses in-process `TestClient`,
which never exercises the real `uvicorn` startup path, real networking, or
real process lifecycle."

Every assertion below is a real HTTP round trip (via `requests`, a real
socket) against a real `uvicorn` subprocess running the exact real
`credit_default_scoring_service.py` this suite documents and ships in its
Docker image -- not FastAPI's in-process `TestClient`. The model bundle is
the same real, genuinely-fit (fake data) fixture
`scripts/generate_ci_fixture_bundles.py` already uses to verify the Docker
image builds and runs in CI, reused here rather than duplicated so this
test needs no real Kaggle data and no locally-run notebook.

This test does NOT replace `tests/test_scoring_services.py` (bit-identical
output verification against an independent reference computation) or
`src/tests/test_rate_limit_common.py`/`test_adverse_action_endpoint.py`
(focused, fast, in-process behavior checks) -- it adds the one thing those
cannot provide: proof the real deployed process actually starts and serves
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
