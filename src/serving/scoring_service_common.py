"""
src/serving/scoring_service_common.py

HYPER shared component: builds a real, deployable FastAPI scoring service from
any of this suite's joblib model bundles that follow the shared contract
{"model", "ordinal_encoder", "imputer", "feature_cols", "numeric_features",
"categorical_features", "champion_name"} (Notebooks 01 and 02 both save this
exact shape -- see pipeline_body.py / pipeline_nb02.py's own final joblib.dump
call). Built once, imported by every per-problem scoring service in this
suite -- not duplicated per problem.

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
objects (not strings) here sidesteps that lookup entirely.
"""
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, create_model


def load_bundle(bundle_path: Path) -> dict:
    if not bundle_path.exists():
        raise FileNotFoundError(
            f"Model bundle not found at {bundle_path}. Run the notebook that trains and "
            "saves this bundle at least once before starting this service."
        )
    return joblib.load(bundle_path)


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

    class ScoreResponse(BaseModel):
        pass

    app = FastAPI(title=title, description=description, version="1.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "champion_model": champion_name,
                "n_numeric_features": len(numeric_features),
                "n_categorical_features": len(categorical_features)}

    @app.get("/schema")
    def schema():
        return {"numeric_features": numeric_features, "categorical_features": categorical_features,
                "champion_model": champion_name}

    @app.post("/score")
    def score(request: RequestModel):
        try:
            proba = score_one(bundle, request.model_dump())
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
        return {score_label: proba, "champion_model": champion_name}

    return app
