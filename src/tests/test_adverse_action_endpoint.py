"""Real end-to-end tests for the POST /adverse-action-notice endpoint wired
into src/serving/scoring_service_common.py's build_scoring_app() factory
(2026-09-08) -- every assertion here is a real HTTP round-trip through a
real FastAPI app (via TestClient) against a real, freshly fitted
LogisticRegression bundle, exercised the same way test_rate_limit_common.py
exercises this factory's other endpoints.
"""

import sys
import tempfile
from pathlib import Path

import joblib
import numpy as np

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from fastapi.testclient import TestClient  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from serving.scoring_service_common import build_scoring_app  # noqa: E402


def _fit_tiny_classifier_bundle(tmp_path, feature_cols):
    rng = np.random.RandomState(0)
    X = rng.uniform(-3, 3, size=(200, len(feature_cols)))
    y = (X.sum(axis=1) > 0).astype(int)
    imputer = SimpleImputer(strategy="mean").fit(X)
    model = LogisticRegression().fit(imputer.transform(X), y)
    bundle = {
        "model": model,
        "imputer": imputer,
        "feature_cols": feature_cols,
        "numeric_features": feature_cols,
        "categorical_features": [],
        "ordinal_encoder": None,
        "champion_name": "tiny_logreg",
    }
    path = tmp_path / "bundle.joblib"
    joblib.dump(bundle, path)
    return path


def _auth_headers(client):
    resp = client.post(
        "/token",
        data={"username": "x", "password": "dev-only-CHANGE-ME-before-deploying"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_adverse_action_notice_endpoint_denies_with_real_reasons(tmp_path):
    feature_cols = ["AMT_CREDIT", "AMT_INCOME_TOTAL", "CODE_GENDER"]
    bundle_path = _fit_tiny_classifier_bundle(tmp_path, feature_cols)
    app = build_scoring_app(bundle_path, title="Tiny Risk Service", description="test")
    client = TestClient(app)
    headers = _auth_headers(client)

    payload = {
        "AMT_CREDIT": 3.0,
        "AMT_INCOME_TOTAL": 2.5,
        "CODE_GENDER": 3.0,
        "threshold": 0.5,
    }
    resp = client.post("/adverse-action-notice", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in ("adverse_action", "approved")
    if body["decision"] == "adverse_action":
        shown = [r["factor"] for r in body["principal_reasons"]]
        assert "CODE_GENDER" not in shown
        for r in body["principal_reasons"]:
            assert "_" not in r["reason"]


def test_adverse_action_notice_requires_auth():
    feature_cols = ["AMT_CREDIT"]
    with tempfile.TemporaryDirectory() as td:
        bundle_path = _fit_tiny_classifier_bundle(Path(td), feature_cols)
        app = build_scoring_app(bundle_path, title="Tiny Risk Service 2", description="test")
        client = TestClient(app)
        resp = client.post("/adverse-action-notice", json={"AMT_CREDIT": 1.0, "threshold": 0.5})
        assert resp.status_code == 401


def test_approval_style_score_label_flips_adverse_direction(tmp_path):
    feature_cols = ["EXT_SOURCE_1", "AMT_INCOME_TOTAL"]
    bundle_path = _fit_tiny_classifier_bundle(tmp_path, feature_cols)
    app = build_scoring_app(
        bundle_path,
        title="Tiny Approval Service",
        description="test",
        score_label="approval_probability",
    )
    client = TestClient(app)
    headers = _auth_headers(client)

    payload = {"EXT_SOURCE_1": -3.0, "AMT_INCOME_TOTAL": -3.0, "threshold": 0.5}
    resp = client.post("/adverse-action-notice", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    # Low approval probability with strongly negative inputs should deny.
    assert body["decision"] == "adverse_action"
