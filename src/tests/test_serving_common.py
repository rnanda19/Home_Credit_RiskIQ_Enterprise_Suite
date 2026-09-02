"""
src/tests/test_serving_common.py

Real tests for the two new HYPER shared serving modules added in the
2026-09-02 hardening pass: src/serving/auth_common.py and
src/serving/explainability_common.py. These are pure-Python, structural
code-correctness tests -- no business data, no notebook artifacts, no
trained model required -- consistent with the standing 2026-09-01
no-fixture-for-business-data verification policy. Every assertion is
computed by direct execution of the real functions under test, never a
mocked or fabricated expectation.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from serving.auth_common import DEV_DEFAULT_API_KEY, configured_api_key, require_api_key  # noqa: E402
from serving.explainability_common import top_reason_codes  # noqa: E402
from serving.scoring_service_common import build_scoring_app  # noqa: E402
from serving.scoring_service_common import load_bundle as load_scoring_bundle  # noqa: E402
from serving.segment_assignment_common import build_segment_app  # noqa: E402
from serving.segment_assignment_common import load_bundle as load_segment_bundle  # noqa: E402


# --------------------------------------------------------------------------
# auth_common.py
# --------------------------------------------------------------------------

def _tiny_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    def protected():
        return {"ok": True}

    return app


def test_configured_api_key_falls_back_to_dev_default_when_unset(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert configured_api_key() == DEV_DEFAULT_API_KEY


def test_configured_api_key_uses_real_env_value_when_set(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    assert configured_api_key() == "a-real-configured-key"


def test_health_endpoint_never_requires_auth(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    client = TestClient(_tiny_app())
    resp = client.get("/health")
    assert resp.status_code == 200


def test_protected_endpoint_rejects_missing_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    client = TestClient(_tiny_app())
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    client = TestClient(_tiny_app())
    resp = client.get("/protected", headers={"X-API-Key": "not-the-right-key"})
    assert resp.status_code == 401


def test_protected_endpoint_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    client = TestClient(_tiny_app())
    resp = client.get("/protected", headers={"X-API-Key": "a-real-configured-key"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_protected_endpoint_accepts_dev_default_when_unset(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    client = TestClient(_tiny_app())
    resp = client.get("/protected", headers={"X-API-Key": DEV_DEFAULT_API_KEY})
    assert resp.status_code == 200


def test_require_api_key_uses_constant_time_comparison():
    """Real regression test for the exact hardening requirement: comparison
    must be secrets.compare_digest, never `==` (which would leak timing)."""
    import inspect

    src = inspect.getsource(require_api_key)
    assert "compare_digest" in src
    assert "presented == expected" not in src.replace(" ", "")


# --------------------------------------------------------------------------
# explainability_common.py
# --------------------------------------------------------------------------

def _linear_predict_fn(weights: dict, base: float):
    """A real, hand-computable scoring function: base + sum(weight * value)
    for each feature, so every occlusion contribution below is independently
    verifiable by hand, not just "does it run"."""
    def _predict(payload: dict) -> float:
        return base + sum(weights.get(f, 0.0) * (payload.get(f) or 0.0) for f in payload)
    return _predict


def test_top_reason_codes_ranks_by_magnitude_of_real_contribution():
    weights = {"income": 0.00001, "age": -0.01, "n_late_payments": 0.05}
    predict_fn = _linear_predict_fn(weights, base=0.5)
    raw_payload = {"income": 50000.0, "age": 40.0, "n_late_payments": 3.0}
    baseline_payload = {"income": 0.0, "age": 0.0, "n_late_payments": 0.0}

    reasons = top_reason_codes(predict_fn, raw_payload, baseline_payload, n=3)

    # Hand-computed expected contributions (base_pred - occluded_pred for
    # each feature reset to its own baseline, one at a time):
    #   income:           0.00001 * 50000.0 =  0.5
    #   age:              -0.01 * 40.0       = -0.4
    #   n_late_payments:  0.05 * 3.0         =  0.15
    assert [r["factor"] for r in reasons] == ["income", "age", "n_late_payments"]
    assert reasons[0]["contribution"] == pytest.approx(0.5, abs=1e-9)
    assert reasons[1]["contribution"] == pytest.approx(-0.4, abs=1e-9)
    assert reasons[2]["contribution"] == pytest.approx(0.15, abs=1e-9)


def test_top_reason_codes_truncates_to_n():
    weights = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
    predict_fn = _linear_predict_fn(weights, base=0.0)
    raw_payload = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    baseline_payload = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}

    reasons = top_reason_codes(predict_fn, raw_payload, baseline_payload, n=2)
    assert len(reasons) == 2
    assert [r["factor"] for r in reasons] == ["d", "c"]


def test_top_reason_codes_is_empty_when_request_matches_baseline_everywhere():
    weights = {"income": 1.0}
    predict_fn = _linear_predict_fn(weights, base=0.0)
    raw_payload = {"income": 0.0}
    baseline_payload = {"income": 0.0}

    reasons = top_reason_codes(predict_fn, raw_payload, baseline_payload, n=3)
    assert reasons == []


def test_top_reason_codes_skips_only_the_features_already_at_baseline():
    weights = {"income": 1.0, "age": 1.0}
    predict_fn = _linear_predict_fn(weights, base=0.0)
    raw_payload = {"income": 100.0, "age": 0.0}  # age already at its own baseline
    baseline_payload = {"income": 0.0, "age": 0.0}

    reasons = top_reason_codes(predict_fn, raw_payload, baseline_payload, n=3)
    assert [r["factor"] for r in reasons] == ["income"]


# --------------------------------------------------------------------------
# scoring_service_common.py / segment_assignment_common.py -- 2026-09-02
# GENERALIZATION for Mega Project 4's simpler real bundle shapes (added
# while hardening MP4; see each module's own docstring). Real, hand-built,
# genuinely-fit (not mocked) sklearn bundles -- structural code-correctness
# tests, no business data.
# --------------------------------------------------------------------------

def _fit_classifier_bundle_no_categoricals(tmp_path):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression

    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 1.0], [2.0, 5.0]])
    y = np.array([0, 1, 0, 1])
    imputer = SimpleImputer(strategy="median").fit(X)
    model = LogisticRegression().fit(imputer.transform(X), y)
    bundle = {"model": model, "imputer": imputer, "feature_cols": ["f1", "f2"],
              "champion_name": "LogisticRegression"}
    bundle_path = tmp_path / "bundle.joblib"
    joblib.dump(bundle, bundle_path)
    return bundle_path


def test_load_bundle_defaults_numeric_only_fields_when_absent(tmp_path):
    bundle_path = _fit_classifier_bundle_no_categoricals(tmp_path)
    loaded = load_scoring_bundle(bundle_path)
    assert loaded["numeric_features"] == ["f1", "f2"]
    assert loaded["categorical_features"] == []
    assert loaded["ordinal_encoder"] is None


def test_load_bundle_leaves_existing_categorical_fields_untouched(tmp_path):
    """A bundle that already carries numeric_features/categorical_features
    (Mega Project 1's shape) must be completely unaffected by the fallback."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import OrdinalEncoder

    X = np.array([[1.0], [3.0], [5.0], [2.0]])
    y = np.array([0, 1, 0, 1])
    imputer = SimpleImputer(strategy="median").fit(X)
    model = LogisticRegression().fit(imputer.transform(X), y)
    enc = OrdinalEncoder().fit([["A"], ["B"]])
    bundle = {"model": model, "imputer": imputer, "ordinal_encoder": enc,
              "feature_cols": ["f1", "cat1"], "numeric_features": ["f1"],
              "categorical_features": ["cat1"], "champion_name": "LogisticRegression"}
    bundle_path = tmp_path / "bundle.joblib"
    joblib.dump(bundle, bundle_path)

    loaded = load_scoring_bundle(bundle_path)
    assert loaded["numeric_features"] == ["f1"]
    assert loaded["categorical_features"] == ["cat1"]
    # joblib round-trips through disk, so identity doesn't survive -- assert
    # the real saved encoder came through untouched (not silently replaced
    # by the fallback), by comparing its fitted categories instead.
    assert loaded["ordinal_encoder"] is not None
    assert [list(c) for c in loaded["ordinal_encoder"].categories_] == [list(c) for c in enc.categories_]


def test_build_scoring_app_serves_a_bundle_with_no_categorical_split(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "testkey")
    bundle_path = _fit_classifier_bundle_no_categoricals(tmp_path)
    app = build_scoring_app(bundle_path, title="TestScoring", description="test",
                             score_label="probability")
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["n_categorical_features"] == 0

    unauth = client.post("/score", json={"f1": 1.0, "f2": 2.0})
    assert unauth.status_code == 401

    resp = client.post("/score", json={"f1": 1.0, "f2": 2.0}, headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert isinstance(body["top_reasons"], list)


def _fit_clustering_bundle_alt_key_names(tmp_path):
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    X = np.array([[1.0, 1.0], [1.1, 0.9], [8.0, 8.0], [8.1, 7.9]])
    scaler = StandardScaler().fit(X)
    kmeans = KMeans(n_clusters=2, random_state=0, n_init=10).fit(scaler.transform(X))
    bundle = {"kmeans": kmeans, "scaler": scaler, "feature_cols": ["a", "b"],
              "pattern_labels": ["Low", "High"], "k_chosen": 2, "silhouette_chosen": 0.9}
    bundle_path = tmp_path / "cbundle.joblib"
    joblib.dump(bundle, bundle_path)
    return bundle_path


def test_segment_load_bundle_aliases_feature_cols_and_pattern_labels(tmp_path):
    bundle_path = _fit_clustering_bundle_alt_key_names(tmp_path)
    loaded = load_segment_bundle(bundle_path)
    assert loaded["feature_names"] == ["a", "b"]
    assert loaded["segment_labels"] == ["Low", "High"]


def test_segment_load_bundle_leaves_canonical_keys_untouched(tmp_path):
    """A bundle that already carries feature_names/segment_labels (Mega
    Project 3's shape) must be completely unaffected by the fallback."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    X = np.array([[1.0, 1.0], [8.0, 8.0]])
    scaler = StandardScaler().fit(X)
    kmeans = KMeans(n_clusters=1, random_state=0, n_init=10).fit(scaler.transform(X))
    bundle = {"kmeans": kmeans, "scaler": scaler, "feature_names": ["x", "y"],
              "segment_labels": ["Only"], "k_chosen": 1}
    bundle_path = tmp_path / "cbundle.joblib"
    joblib.dump(bundle, bundle_path)

    loaded = load_segment_bundle(bundle_path)
    assert loaded["feature_names"] == ["x", "y"]
    assert loaded["segment_labels"] == ["Only"]


def test_build_segment_app_serves_a_bundle_with_alternate_key_names(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "testkey")
    bundle_path = _fit_clustering_bundle_alt_key_names(tmp_path)
    app = build_segment_app(bundle_path, title="TestSegment", description="test",
                             segment_field_name="pattern", history_flag_note="note")
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["k_chosen"] == 2

    unauth = client.post("/score", json={"a": 1.0, "b": 1.0})
    assert unauth.status_code == 401

    resp = client.post("/score", json={"a": 1.0, "b": 1.0}, headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pattern"] == "High"
    assert len(body["distance_to_each_segment"]) == 2
    # nearest-first: the assigned segment's own distance sorts first
    assert body["distance_to_each_segment"][0]["segment"] == "High"
