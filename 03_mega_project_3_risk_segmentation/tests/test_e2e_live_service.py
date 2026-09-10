"""
Real end-to-end integration tests for all 4 of MP3's deployable services
(Problem 2 added 2026-09-08; Problems 1/3/4 added 2026-09-10) -- see MP1's
own `tests/test_e2e_live_service.py` module docstring for the full real gap
this closes. Deliberately covers two different real app shapes: a
clustering `segment_assignment_common`-built service (Problems 2/3/4) and a
hand-built, deterministic-lookup service with no trained model at all
(Problem 1) -- proving `src/testing/e2e_process_harness.py` is a real,
generalized HYPER component, not hardcoded to any one service shape.

Problem 5 (Cross-Axis Risk-Return Synthesis) has no service here by design
-- it is a population-level analysis, not a per-record scoring problem; see
this Mega Project's own README for the disclosed scope boundary.
"""

import json
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
PORT_TIER = 8907
PORT_REPAYMENT = 8908
PORT_UTILIZATION = 8909
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


# ---------------------------------------------------------------------------
# Problem 1 -- Data-Driven Risk Tier Construction (risk_tier_assignment_service.py)
#
# A hand-built, deterministic-lookup service -- no trained model, no
# clustering bundle. Applies the real fixture tier edges
# generate_ci_fixture_bundles.py's own summary JSON declares
# ([None, 0.3, 0.6, None] -> reconstructed as [-inf, 0.3, 0.6, inf]) via the
# service's own pd.cut()-equivalent lookup. Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_tier(tmp_path):
    """Real subprocess-launched instance of the risk-tier service, pointed
    at a real (fixture) summary JSON -- the same shape
    scripts/generate_ci_fixture_bundles.py writes for Docker CI
    verification."""
    summary_path = tmp_path / "notebook_01_summary.json"
    summary_path.write_text(json.dumps({"tiering_config": {"tier_bin_edges": [None, 0.3, 0.6, None]}}))
    env = {
        "NB01_SUMMARY_PATH": str(summary_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="risk_tier_assignment_service",
        service_dir=SERVICE_DIR,
        port=PORT_TIER,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_tier_health_is_open_and_reports_the_real_fixture_edges(live_service_tier):
    resp = requests.get(f"{live_service_tier}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["n_real_tiers"] == 3


def test_tier_schema_and_score_reject_missing_auth_over_real_http(live_service_tier):
    resp = requests.get(f"{live_service_tier}/schema", timeout=5)
    assert resp.status_code == 401
    resp = requests.post(f"{live_service_tier}/score", json={"PD": 0.1}, timeout=5)
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "pd_value,expected_tier,expected_index",
    [
        (0.1, "Tier 1", 0),  # (-inf, 0.3]
        (0.5, "Tier 2", 1),  # (0.3, 0.6]
        (0.9, "Tier 3", 2),  # (0.6, inf)
    ],
)
def test_tier_real_score_call_matches_the_real_fixture_edges(
    live_service_tier, pd_value, expected_tier, expected_index
):
    resp = requests.post(
        f"{live_service_tier}/score",
        json={"PD": pd_value},
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_tier"] == expected_tier
    assert body["tier_index"] == expected_index


# ---------------------------------------------------------------------------
# Problem 3 -- Repayment Behavior Segmentation (repayment_segment_assignment_service.py)
#
# Same build_segment_app() factory as Problem 2's bureau service, different
# bundle env var (NB03_SEGMENT_MODEL_PATH) and segment field name
# ("repayment_segment"). Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_repayment(tmp_path):
    bundle_path = tmp_path / "notebook_03_segment_model.joblib"
    joblib.dump(segment_bundle(), bundle_path)
    env = {
        "NB03_SEGMENT_MODEL_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="repayment_segment_assignment_service",
        service_dir=SERVICE_DIR,
        port=PORT_REPAYMENT,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_repayment_health_is_open_and_reports_the_real_fixture_model(
    live_service_repayment,
):
    resp = requests.get(f"{live_service_repayment}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["k_chosen"] == 2


def test_repayment_score_rejects_missing_auth_over_real_http(live_service_repayment):
    resp = requests.post(f"{live_service_repayment}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_repayment_real_score_call_over_x_api_key_auth(live_service_repayment):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_repayment}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["repayment_segment"] in ("Fixture Segment A", "Fixture Segment B")
    assert len(body["distance_to_each_segment"]) == 2


# ---------------------------------------------------------------------------
# Problem 4 -- Revolving Credit Utilization Segmentation (utilization_segment_assignment_service.py)
#
# Same build_segment_app() factory again, NB04_SEGMENT_MODEL_PATH and
# "utilization_segment". Added 2026-09-10.
# ---------------------------------------------------------------------------


@pytest.fixture()
def live_service_utilization(tmp_path):
    bundle_path = tmp_path / "notebook_04_segment_model.joblib"
    joblib.dump(segment_bundle(), bundle_path)
    env = {
        "NB04_SEGMENT_MODEL_PATH": str(bundle_path),
        "API_KEY": TEST_API_KEY,
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
    }
    with run_service_subprocess(
        module_name="utilization_segment_assignment_service",
        service_dir=SERVICE_DIR,
        port=PORT_UTILIZATION,
        env_overrides=env,
    ) as base_url:
        yield base_url


def test_utilization_health_is_open_and_reports_the_real_fixture_model(
    live_service_utilization,
):
    resp = requests.get(f"{live_service_utilization}/health", timeout=5)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["k_chosen"] == 2


def test_utilization_score_rejects_missing_auth_over_real_http(
    live_service_utilization,
):
    resp = requests.post(f"{live_service_utilization}/score", json={}, timeout=5)
    assert resp.status_code == 401


def test_utilization_real_score_call_over_x_api_key_auth(live_service_utilization):
    payload = {"ci_fixture_feature_1": 2.0, "ci_fixture_feature_2": 3.0}
    resp = requests.post(
        f"{live_service_utilization}/score",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
        timeout=5,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["utilization_segment"] in ("Fixture Segment A", "Fixture Segment B")
    assert len(body["distance_to_each_segment"]) == 2
