"""
Real end-to-end integration tests for all 4 of MP4's deployable services
(early_delinquency_scoring_service.py, payment_pattern_assignment_service.py,
revolving_distress_scoring_service.py, pos_cash_trajectory_scoring_service.py).
Added 2026-09-10 -- MP4 previously had zero services covered this way (see
MP1's own `tests/test_e2e_live_service.py` module docstring for the full
real gap this closes across the suite).

Every assertion below is a real HTTP round trip (via `requests`, a real
socket) against a real `uvicorn` subprocess running the exact real service
module this suite documents and ships in its Docker image -- not FastAPI's
in-process `TestClient`. All 4 services are built by this suite's shared
`build_scoring_app()`/`build_segment_app()` factories (Problems 1/3/4 and
Problem 2 respectively) -- the same two real app shapes already proven by
MP1's and MP3's own end-to-end suites. Model bundles are the same real,
genuinely-fit (fake data) fixtures `scripts/generate_ci_fixture_bundles.py`
already uses to verify the Docker image builds and runs in CI, reused here
rather than duplicated so these tests need no real Kaggle data and no
locally-run notebook.

These tests do NOT replace `tests/test_scoring_services.py` (bit-identical
output verification against an independent reference computation) -- they
add the one thing that cannot provide: proof each real deployed process
actually starts and serves real traffic end to end.
"""

import sys
from pathlib import Path

import joblib
import pytest
import requests

THIS_DIR = Path(__file__).resolve().parent
MP4_DIR = THIS_DIR.parent
SUITE_ROOT = MP4_DIR.parent
SERVICE_DIR = MP4_DIR / "services"

sys.path.insert(0, str(SUITE_ROOT / "src"))
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from testing.e2e_process_harness import run_service_subprocess  # noqa: E402
from generate_ci_fixture_bundles import scoring_bundle, segment_bundle  # noqa: E402

PORT_P1 = 8911
PORT_P2 = 8912
PORT_P3 = 8913
PORT_P4 = 8914
TEST_API_KEY = "e2e-pytest-only-test-key"
TEST_JWT_SECRET = "e2e-pytest-only-test-jwt-secret"


# ---------------------------------------------------------------------------
# Problem 1 -- Early Delinquency Risk Scoring (early_delinquency_scoring_service.py)
# build_scoring_app() factory, same shape as MP1 Problem 1.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p1(tmp_path):
    bundle_path = tmp_path / "notebook_01_champion_model.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB01_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="early_delinquency_scoring_service",
        service_dir=SERVICE_DIR,
        port=PORT_P1,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p1_health_is_open_and_reports_the_real_fixture_model(live_service_p1):
    resp = requests.get(f"{live_service_p1}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["champion_model"]


def test_p1_schema_and_score_reject_missing_auth_over_real_http(live_service_p1):
    resp = requests.get(f"{live_service_p1}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_p1}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p1_real_oauth2_token_flow_then_authenticated_schema_call(live_service_p1):
    token_resp = requests.post(
        f"{live_service_p1}/token",
        data={"username": "e2e", "password": TEST_API_KEY},
        timeout=5,
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]

    schema_resp = requests.get(
        f"{live_service_p1}/schema",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert schema_resp.status_code == 200
    assert "ci_fixture_feature_1" in schema_resp.json()["numeric_features"]


def test_p1_real_score_call_over_x_api_key_auth(live_service_p1):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_p1}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert isinstance(body["top_reasons"], list)


def test_p1_real_adverse_action_notice_call_end_to_end(live_service_p1):
    payload = {
        "ci_fixture_feature_1": 5.0,
        "ci_fixture_feature_2": 5.0,
        "threshold": 0.0,
    }
    resp = requests.post(
        f"{live_service_p1}/adverse-action-notice",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("adverse_action", "approved")
    assert "principal_reasons" in body and "suppressed_factors" in body


# ---------------------------------------------------------------------------
# Problem 2 -- Installment Payment Behavior Detection (payment_pattern_assignment_service.py)
# build_segment_app() factory, same shape as MP3's segment services.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p2(tmp_path):
    bundle_path = tmp_path / "notebook_02_kmeans_model.joblib"
    joblib.dump(segment_bundle(), bundle_path)
    env = {
        "NB02_KMEANS_MODEL_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="payment_pattern_assignment_service",
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
    assert body["k_chosen"] == 2


def test_p2_score_rejects_missing_auth_over_real_http(live_service_p2):
    resp = requests.post(f"{live_service_p2}/score", json={}, timeout=5)
    assert resp.status_code == 401


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
    assert body["payment_pattern"] in ("Fixture Segment A", "Fixture Segment B")
    assert len(body["distance_to_each_segment"]) == 2


# ---------------------------------------------------------------------------
# Problem 3 -- Revolving/Credit-Card Distress Early Warning (revolving_distress_scoring_service.py)
# build_scoring_app() factory, same shape as Problem 1 above.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p3(tmp_path):
    bundle_path = tmp_path / "notebook_03_champion_model.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB03_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="revolving_distress_scoring_service",
        service_dir=SERVICE_DIR,
        port=PORT_P3,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p3_health_is_open_and_reports_the_real_fixture_model(live_service_p3):
    resp = requests.get(f"{live_service_p3}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["champion_model"]


def test_p3_schema_and_score_reject_missing_auth_over_real_http(live_service_p3):
    resp = requests.get(f"{live_service_p3}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_p3}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p3_real_score_call_over_x_api_key_auth(live_service_p3):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_p3}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert isinstance(body["top_reasons"], list)


# ---------------------------------------------------------------------------
# Problem 4 -- POS/Cash Loan Delinquency Trajectory (pos_cash_trajectory_scoring_service.py)
# build_scoring_app() factory, same shape as Problems 1/3 above.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_p4(tmp_path):
    bundle_path = tmp_path / "notebook_04_champion_model.joblib"
    joblib.dump(scoring_bundle(), bundle_path)
    env = {
        "NB04_BUNDLE_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="pos_cash_trajectory_scoring_service",
        service_dir=SERVICE_DIR,
        port=PORT_P4,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_p4_health_is_open_and_reports_the_real_fixture_model(live_service_p4):
    resp = requests.get(f"{live_service_p4}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "CI fixture" in body["champion_model"]


def test_p4_schema_and_score_reject_missing_auth_over_real_http(live_service_p4):
    resp = requests.get(f"{live_service_p4}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_p4}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_p4_real_score_call_over_x_api_key_auth(live_service_p4):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_p4}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert isinstance(body["top_reasons"], list)
