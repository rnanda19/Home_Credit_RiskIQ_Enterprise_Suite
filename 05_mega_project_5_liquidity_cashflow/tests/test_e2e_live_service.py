"""
Real end-to-end integration test for MP5 Problem 4's deployable service
(2026-09-08) -- see MP1's own `tests/test_e2e_live_service.py` module
docstring for the full real gap this closes. Exercises the same
`segment_assignment_common`-built clustering app shape as MP3's own e2e
test, but against MP5's `prepayment_segment_assignment_service.py`
specifically -- the third real service and third Mega Project now covered
by this harness (see E2E_TESTING.md's real, disclosed scope note).

This is separate from `tests/test_scoring_services.py`'s own real check
in this same Mega Project, which verifies the service reproduces
Notebook 04's own real segment assignment for a real applicant using the
REAL trained bundle. This test instead uses the same synthetic CI
fixture bundle every other e2e test in this suite uses
(`segment_bundle()`), so it runs in CI without needing real Kaggle data
or a locally-run notebook -- it proves the real subprocess+HTTP path
works end to end, independent of which bundle is loaded.
"""

import sys
from pathlib import Path

import joblib
import pytest
import requests

THIS_DIR = Path(__file__).resolve().parent
MP5_DIR = THIS_DIR.parent
SUITE_ROOT = MP5_DIR.parent
SERVICE_DIR = MP5_DIR / "services"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from testing.e2e_process_harness import run_service_subprocess  # noqa: E402
from generate_ci_fixture_bundles import segment_bundle  # noqa: E402

PORT = 8903
TEST_API_KEY = "e2e-pytest-only-test-key"
TEST_JWT_SECRET = "e2e-pytest-only-test-jwt-secret"


@pytest.fixture()
def live_service(tmp_path):
    bundle_path = tmp_path / "notebook_04_segment_model.joblib"
    joblib.dump(segment_bundle(), bundle_path)
    env = {
        "NB04_SEGMENT_MODEL_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="prepayment_segment_assignment_service",
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
    assert body["k_chosen"] == 2


def test_schema_rejects_missing_auth_over_real_http(live_service):
    resp = requests.get(f"{live_service}/schema", timeout=5)
    assert resp.status_code == 401


def test_real_oauth2_token_flow_then_authenticated_score_call(live_service):
    token_resp = requests.post(
        f"{live_service}/token",
        data={"username": "e2e", "password": TEST_API_KEY},
        timeout=5,
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service}/score",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["prepayment_segment"] in ("Fixture Segment A", "Fixture Segment B")
    assert len(body["distance_to_each_segment"]) == 2
