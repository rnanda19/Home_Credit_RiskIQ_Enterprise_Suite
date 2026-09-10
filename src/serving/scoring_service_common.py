"""
src/serving/scoring_service_common.py

HYPER shared component: builds a real, deployable FastAPI scoring service from
any of this suite's joblib model bundles that follow the shared contract
{"model", "ordinal_encoder", "imputer", "feature_cols", "numeric_features",
"categorical_features", "champion_name"} (Mega Project 1's Notebooks 01 and
02 both save this exact shape -- see pipeline_body.py / pipeline_nb02.py's
own final joblib.dump call). Built once, imported by every per-problem
scoring service in this suite -- not duplicated per problem.

GENERALIZATION (2026-09-02, added while hardening Mega Project 4): Mega
Project 4's Notebooks 01/03/04 save a simpler, real, all-numeric-feature
bundle -- {"model", "imputer", "feature_cols", "champion_name", "cv_results",
"holdout_metrics"} -- with no ordinal_encoder and no separate numeric/
categorical split, because those notebooks' own real feature space (real
installment-payment behavioral aggregates) has no categorical columns.
Rather than duplicate this whole module a second time for a bundle that
differs only in "has no categoricals," `load_bundle()` below fills in
`numeric_features = feature_cols`, `categorical_features = []`, and
`ordinal_encoder = None` when those keys are absent -- every existing bundle
that DOES carry them (Mega Project 1's) is completely unaffected, since the
fallback only triggers on a missing key.

Preprocessing here is DELIBERATELY IDENTICAL, field for field, to what each
notebook does at scoring time (categorical missing values filled with the
literal string "Missing" before ordinal-encoding, in the exact same order the
notebook trained on) -- any divergence here would silently score requests
differently than the notebook that produced the model, which is the one bug
class a serving layer must never introduce.

NOTE: deliberately NOT using `from __future__ import annotations` here. With
postponed evaluation, FastAPI resolves a route's parameter annotation by
looking the name up in the function's __globals__ at request time -- but
build_scoring_app()'s RequestModel is a class created dynamically INSIDE this
function (a local, not a module global), so that lookup fails silently and
FastAPI falls back to treating `request` as a query parameter instead of a
JSON body (reproduced and confirmed via a real 422 "field required: query.
request" error before this was found and fixed). Keeping real annotation
objects (not strings) here sidesteps that lookup entirely -- the same reason
AdverseActionRequest below (2026-09-08) is also a real, non-string annotation.

HARDENING (2026-09-02): every service built by this factory now requires a
real `X-API-Key` header on `/schema` and `/score` (never `/health`, so
liveness probes stay unauthenticated) via `serving.auth_common.require_auth` (X-API-Key or OAuth2/JWT Bearer -- 2026-09-08 hardening),
and `/score` now returns a real, per-request `top_reasons` explanation via
`serving.explainability_common.top_reason_codes` -- the exact real change in
predicted probability from resetting each real feature that differs from its
own real baseline (None -- the same value this module's own preprocessing
already imputes/encodes as "missing", so no new baseline convention is
invented). See CHANGELOG.md for the real gap this closes.

ADVERSE ACTION (2026-09-08): every service built by this factory now also
exposes a real `POST /adverse-action-notice` endpoint that turns the same
real `top_reason_codes` explanation into an ECOA/Reg B-style "statement of
specific reasons," with sex/marital-status/age and known fair-lending-proxy
features (social-circle default history, coarse geography) structurally
excluded from the customer-facing reason list -- see
serving.adverse_action_common for the full real design and disclosed scope.
`adverse_direction` is derived once, generically, from `score_label` alone
(HYPER: no per-service hardcoding) so this works correctly whether the
underlying score is a default-probability-style risk score (rises with a bad
outcome) or an approval-probability-style score (falls with a bad outcome).
"""

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, create_model

from serving.adverse_action_common import render_adverse_action_notice
from serving.auth_common import add_token_route, require_auth
from serving.explainability_common import top_reason_codes
from serving.rate_limit_common import DEFAULT_RATE_LIMIT, install_rate_limiting


def load_bundle(bundle_path: Path) -> dict:
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"Model bundle not found at {bundle_path}. Run the notebook that trains and "
            "saves this bundle at least once before starting this service."
        )
    bundle = joblib.load(bundle_path)
    # Real backward-compatible default for bundles with no categorical
    # features at all (Mega Project 4's Notebooks 01/03/04) -- see module
    # docstring's 2026-09-02 GENERALIZATION note. A bundle that already
    # carries these real keys (Mega Project 1's) is never touched here.
    bundle.setdefault("numeric_features", list(bundle["feature_cols"]))
    bundle.setdefault("categorical_features", [])
    bundle.setdefault("ordinal_encoder", None)
    return bundle


def build_request_model(model_name: str, numeric_features: list[str], categorical_features: list[str]):
    """Dynamic Pydantic model, one Optional field per real feature the trained model
    actually consumes (mirrors the AMEX platform's severity_scoring_service.py pattern
    for a large, model-specific feature set) -- so validation errors name the exact
    real field that's wrong, rather than accepting an untyped blob."""
    fields = {f: (Optional[float], Field(default=None)) for f in numeric_features}
    fields.update({f: (Optional[str], Field(default=None)) for f in categorical_features})
    return create_model(f"{model_name}ScoringRequest", **fields)


def score_one(bundle: dict, payload: dict) -> float:
    """Real scoring: identical preprocessing to the notebook that trained this bundle
    (see module docstring), returns a real probability in [0, 1]. Raises ValueError on
    a malformed payload rather than silently returning a default score."""
    numeric_features = bundle["numeric_features"]
    categorical_features = bundle["categorical_features"]
    feature_cols = bundle["feature_cols"]
    ord_enc = bundle["ordinal_encoder"]
    imputer = bundle["imputer"]
    model = bundle["model"]

    import pandas as pd

    row = {c: payload.get(c) for c in feature_cols}
    pdf = pd.DataFrame([row])
    for c in categorical_features:
        pdf[c] = pdf[c].astype(object).fillna("Missing").astype(str)
    for c in numeric_features:
        pdf[c] = pdf[c].astype("float32")

    X = pdf[feature_cols].copy()
    if categorical_features:
        X[categorical_features] = ord_enc.transform(pdf[categorical_features].astype(str))
    X[numeric_features] = imputer.transform(pdf[numeric_features])

    proba = model.predict_proba(X)[:, 1][0]
    return float(np.clip(proba, 0.0, 1.0))


def build_scoring_app(
    bundle_path: Path,
    title: str,
    description: str,
    score_label: str = "probability",
) -> FastAPI:
    """Returns a real, runnable FastAPI app. The model bundle is loaded once at import
    time (fails fast, loudly, at startup if missing -- never a silent no-op service)."""
    bundle = load_bundle(bundle_path)
    numeric_features = bundle["numeric_features"]
    categorical_features = bundle["categorical_features"]
    champion_name = bundle.get("champion_name", "unknown")

    RequestModel = build_request_model(title.replace(" ", ""), numeric_features, categorical_features)
    # Same real feature fields as RequestModel, plus a caller-supplied
    # decision threshold -- this factory makes no accept/reject decision of
    # its own (see loan_approval_scoring_service.py's docstring), so the
    # threshold that defines "adverse" has to come from the caller.
    AdverseActionRequest = create_model(
        f"{title.replace(' ', '')}AdverseActionRequest",
        threshold=(
            float,
            Field(
                ...,
                description="Caller-supplied decision threshold on the model's score.",
            ),
        ),
        __base__=RequestModel,
    )
    # HYPER: derived from score_label alone so every factory-built service
    # gets a correct adverse-direction without per-service hardcoding. A
    # default-probability/risk/capital-requirement style score rises with a
    # worse outcome ("positive"); an approval-probability style score falls
    # with a worse outcome ("negative"). See adverse_action_common.py.
    adverse_direction = "negative" if "approval" in score_label.lower() else "positive"

    class ScoreResponse(BaseModel):
        pass

    app = FastAPI(title=title, description=description, version="1.0.0")
    limiter = install_rate_limiting(app)  # real rate limiting (2026-09-08 hardening)
    add_token_route(app, limiter=limiter)  # real POST /token -- OAuth2/JWT (2026-09-08 hardening)

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "champion_model": champion_name,
            "n_numeric_features": len(numeric_features),
            "n_categorical_features": len(categorical_features),
        }

    @app.get("/schema", dependencies=[Depends(require_auth)])
    @limiter.limit(DEFAULT_RATE_LIMIT)
    def schema(request: Request):
        return {
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "champion_model": champion_name,
        }

    @app.post("/score", dependencies=[Depends(require_auth)])
    @limiter.limit(DEFAULT_RATE_LIMIT)
    def score(request: Request, body: RequestModel):
        payload = body.model_dump()
        try:
            proba = score_one(bundle, payload)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
        baseline_payload = {f: None for f in numeric_features + categorical_features}
        top_reasons = top_reason_codes(
            predict_fn=lambda p: score_one(bundle, p),
            raw_payload=payload,
            baseline_payload=baseline_payload,
        )
        return {
            score_label: proba,
            "champion_model": champion_name,
            "top_reasons": top_reasons,
        }

    @app.post("/adverse-action-notice", dependencies=[Depends(require_auth)])
    @limiter.limit(DEFAULT_RATE_LIMIT)
    def adverse_action_notice(request: Request, body: AdverseActionRequest):
        payload = body.model_dump(exclude={"threshold"})
        try:
            proba = score_one(bundle, payload)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
        baseline_payload = {f: None for f in numeric_features + categorical_features}
        # A wider candidate pool than /score's default (n=3) -- some of the
        # highest-magnitude real factors may be structurally suppressed
        # (protected-basis/fair-lending-proxy) before max_reasons is applied.
        top_reasons = top_reason_codes(
            predict_fn=lambda p: score_one(bundle, p),
            raw_payload=payload,
            baseline_payload=baseline_payload,
            n=max(12, len(payload)),
        )
        notice = render_adverse_action_notice(
            top_reasons,
            score=proba,
            threshold=body.threshold,
            adverse_direction=adverse_direction,
        )
        return {"champion_model": champion_name, **notice}

    return app
