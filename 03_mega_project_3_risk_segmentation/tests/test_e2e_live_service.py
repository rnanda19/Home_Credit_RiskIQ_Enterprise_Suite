"""
Real end-to-end integration test for MP3 Problem 2's deployable service
(2026-09-08) -- see MP1's own `tests/test_e2e_live_service.py` module
docstring for the full real gap this closes. Deliberately exercises a
different real app shape (a clustering `segment_assignment_common`-built
service, not a classifier `scoring_service_common`-built one) against the
same `src/testing/e2e_process_harness.py` to prove the harness is a real,
generalized HYPER component -- not hardcoded to MP1's one service.
"""

import sys
from pathlib import Path

import joblib
import pytest
import requests

THIS_DIR = Path(__file__).resolve().parent
MP3_DIR = THIS_DIR.parent
SUITE_ROOT = MP3_DIR.parent
SERVICE_DIR = MP3_DIR / "services"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from testing.e2e_process_harness import run_service_subprocess  # noqa: E402
from generate_ci_fixture_bundles import segment_bundle  # noqa: E402

PORT = 8902
TEST_API_KEY = "e2e-pytest-only-test-key"
TEST_JWT_SECRET = "e2e-pytest-only-test-jwt-secret"


@pytest.fixture()
def live_service(tmp_path):
    bundle_path = tmp_path / "notebook_02_segment_model.joblib"
    joblib.dump(segment_bundle(), bundle_path)
    env = {
        "NB02_SEGMENT_MODEL_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="bureau_segment_assignment_service",
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
    assert body["bureau_segment"] in ("Fixture Segment A", "Fixture Segment B")
    assert len(body["distance_to_each_segment"]) == 2
