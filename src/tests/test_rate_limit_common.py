"""Real tests for src/serving/rate_limit_common.py (2026-09-08 hardening) --
closes the disclosed gap: "No rate limiting or TLS termination anywhere
in the service layer -- every endpoint accepts unlimited plain-HTTP
requests today." Every assertion here is a real HTTP round-trip through a
real FastAPI app (via TestClient) against a real, in-memory slowapi
Limiter -- no mocked rate-limit state.
"""

import sys
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from serving.auth_common import add_token_route  # noqa: E402
from serving.rate_limit_common import (  # noqa: E402
    DEFAULT_RATE_LIMIT,
    TOKEN_RATE_LIMIT,
    install_rate_limiting,
)
from serving.scoring_service_common import build_scoring_app  # noqa: E402


def _fit_tiny_classifier_bundle(tmp_path):
    """Same real, minimal, synthetic-fixture style as
    test_serving_common.py's own bundle helpers -- a real fitted model,
    tiny data, not a mock."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression

    X = np.array([[0.0, 1.0], [1.0, 0.0], [2.0, 2.0], [3.0, 1.0]])
    y = np.array([0, 0, 1, 1])
    imputer = SimpleImputer(strategy="median").fit(X)
    model = LogisticRegression().fit(imputer.transform(X), y)
    bundle = {
        "model": model,
        "imputer": imputer,
        "feature_cols": ["f1", "f2"],
        "champion_name": "LogisticRegression",
    }
    bundle_path = tmp_path / "bundle.joblib"
    joblib.dump(bundle, bundle_path)
    return bundle_path


def test_install_rate_limiting_returns_a_working_limiter_on_a_tiny_app():
    app = FastAPI()
    limiter = install_rate_limiting(app)

    @app.get("/limited")
    @limiter.limit("3/minute")
    def limited(request: Request):
        return {"ok": True}

    client = TestClient(app)
    codes = [client.get("/limited").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429], codes


def test_health_is_never_rate_limited_even_after_the_limit_trips():
    app = FastAPI()
    limiter = install_rate_limiting(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/limited")
    @limiter.limit("2/minute")
    def limited(request: Request):
        return {"ok": True}

    client = TestClient(app)
    for _ in range(4):
        client.get("/limited")
    # /limited is now well past its own limit -- /health must be unaffected.
    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_token_route_is_rate_limited_when_a_limiter_is_passed(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    app = FastAPI()
    limiter = install_rate_limiting(app)
    add_token_route(app, limiter=limiter)
    client = TestClient(app)

    codes = []
    for _ in range(int(TOKEN_RATE_LIMIT.split("/")[0]) + 2):
        resp = client.post(
            "/token", data={"username": "anything", "password": "a-real-configured-key"}
        )
        codes.append(resp.status_code)
    assert codes.count(429) == 2, codes
    assert codes[:-2] == [200] * (len(codes) - 2)


def test_token_route_is_unlimited_when_no_limiter_is_passed_backward_compat(
    monkeypatch,
):
    """add_token_route(app) with no limiter -- e.g. test_serving_common.py's
    own _tiny_authenticated_app() helper -- must keep working exactly as
    before this hardening, unlimited."""
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    app = FastAPI()
    add_token_route(app)  # no limiter passed
    client = TestClient(app)

    limit_count = int(TOKEN_RATE_LIMIT.split("/")[0])
    for _ in range(limit_count + 5):
        resp = client.post(
            "/token", data={"username": "anything", "password": "a-real-configured-key"}
        )
        assert resp.status_code == 200


def test_real_scoring_service_score_endpoint_rate_limits_for_real(
    tmp_path, monkeypatch
):
    """End-to-end proof against the real shared factory (not a synthetic
    stand-in): build_scoring_app() wires install_rate_limiting() +
    DEFAULT_RATE_LIMIT onto /score exactly as every real deployable
    service in this suite does."""
    monkeypatch.setenv("API_KEY", "testkey")
    bundle_path = _fit_tiny_classifier_bundle(tmp_path)
    app = build_scoring_app(
        bundle_path, title="RLTest", description="test", score_label="probability"
    )
    client = TestClient(app)
    headers = {"X-API-Key": "testkey"}
    payload = {"f1": 1.0, "f2": 2.0}

    limit_count = int(DEFAULT_RATE_LIMIT.split("/")[0])
    codes = [
        client.post("/score", json=payload, headers=headers).status_code
        for _ in range(limit_count + 3)
    ]
    assert codes[:limit_count] == [200] * limit_count, codes
    assert codes[limit_count:] == [429] * 3, codes

    # /health on the same real app must remain completely unaffected.
    assert client.get("/health").status_code == 200


def test_require_auth_dependency_still_runs_before_rate_limiting_denies_bad_creds(
    tmp_path, monkeypatch
):
    """A caller with no/bad credentials still gets a real 401, not a 429 --
    auth and rate limiting are independent, correctly-ordered checks."""
    monkeypatch.setenv("API_KEY", "testkey")
    bundle_path = _fit_tiny_classifier_bundle(tmp_path)
    app = build_scoring_app(
        bundle_path, title="RLTest2", description="test", score_label="probability"
    )
    client = TestClient(app)

    resp = client.post("/score", json={"f1": 1.0, "f2": 2.0})
    assert resp.status_code == 401
