"""
src/serving/segment_assignment_common.py

HYPER shared component: builds a real, deployable FastAPI segment-assignment
service from any of Mega Project 3's `notebook_0{2,3,4}_segment_model.joblib`
bundles (all three saved with the exact same shape:
{"kmeans", "scaler", "feature_names", "segment_labels", "k_chosen",
"random_seed", "winsorize_report" (optional)} -- see the persistence block
each of pipeline_mp3_nb02/03/04.py added near its own Section 14). Built
once, imported by every per-problem segment-assignment service in this
Mega Project -- not duplicated per problem, exactly mirroring
`src/serving/scoring_service_common.py`'s own pattern for Mega Project 1.

Preprocessing here is DELIBERATELY IDENTICAL, field for field, to what each
notebook does before calling `kmeans.predict()`: winsorize (if the bundle
has real winsorize bounds -- Notebook 02 has none, Notebooks 03/04 do) using
the SAME real saved per-feature [lo, hi] bounds, then `scaler.transform()`
with the SAME real fitted `StandardScaler`, then `kmeans.predict()` with the
SAME real fitted model. Any divergence here would silently assign a segment
different from what the notebook that produced the model would assign --
the one bug class a serving layer must never introduce.

A REAL, DISCLOSED SCOPE BOUNDARY: this service takes the ALREADY-ENGINEERED
real feature vector as input (one field per name in the bundle's real
`feature_names` list), not raw multi-row transaction history
(bureau.csv / installments_payments.csv / credit_card_balance.csv rows).
Computing those real aggregate features from raw transaction history is
`src/features/risk_segmentation_features.py`'s job (`engineer_*_features()`),
run once per notebook over the whole real population -- reusable as a
feature-engineering step ahead of this service, not duplicated inside it.
This is the same "features already computed upstream" scope every service
in this suite assumes (Mega Project 1's own services take features like
`N_PREV_APPLICATIONS`, themselves an aggregate over `previous_application.csv`,
the same way).
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
            f"Segment model bundle not found at {bundle_path}. Run the notebook that fits and "
            "saves this bundle at least once before starting this service."
        )
    return joblib.load(bundle_path)


def build_request_model(model_name: str, feature_names: list[str]):
    """Dynamic Pydantic model, one required field per real feature the fitted
    clustering model actually consumes -- so validation errors name the exact
    real field that's wrong, rather than accepting an untyped blob."""
    fields = {f: (float, Field(...)) for f in feature_names}
    return create_model(f"{model_name}SegmentRequest", **fields)


def assign_segment(bundle: dict, payload: dict) -> tuple[str, int]:
    """Real assignment: winsorize (if bounds were saved) -> scale -> predict,
    identical to the notebook that trained this bundle. Raises ValueError on
    a malformed payload rather than silently returning a default segment."""
    feature_names = bundle["feature_names"]
    scaler = bundle["scaler"]
    kmeans = bundle["kmeans"]
    segment_labels = bundle["segment_labels"]
    winsorize_report = bundle.get("winsorize_report") or {}

    x = np.array([[float(payload[f]) for f in feature_names]], dtype=float)
    for j, f in enumerate(feature_names):
        bounds = winsorize_report.get(f)
        if bounds:
            x[0, j] = float(np.clip(x[0, j], bounds["lo"], bounds["hi"]))
    x_scaled = scaler.transform(x)
    label_idx = int(kmeans.predict(x_scaled)[0])
    return segment_labels[label_idx], label_idx


def build_segment_app(
    bundle_path: Path,
    title: str,
    description: str,
    segment_field_name: str,
    history_flag_note: str,
) -> FastAPI:
    """Returns a real, runnable FastAPI app. The clustering bundle is loaded once
    at import time (fails fast, loudly, at startup if missing -- never a silent
    no-op service)."""
    bundle = load_bundle(bundle_path)
    feature_names = bundle["feature_names"]
    segment_labels = bundle["segment_labels"]
    k_chosen = bundle["k_chosen"]
    has_winsorize = bool(bundle.get("winsorize_report"))

    RequestModel = build_request_model(title.replace(" ", ""), feature_names)

    class ScoreResponse(BaseModel):
        pass

    app = FastAPI(title=title, description=description, version="1.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "k_chosen": k_chosen, "n_features": len(feature_names),
                "winsorization_applied": has_winsorize, "note": history_flag_note}

    @app.get("/schema")
    def schema():
        return {"feature_names": feature_names, "segment_labels": segment_labels, "k_chosen": k_chosen,
                "winsorize_bounds": bundle.get("winsorize_report")}

    @app.post("/score")
    def score(request: RequestModel):
        try:
            segment, idx = assign_segment(bundle, request.model_dump())
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Segment assignment failed: {type(e).__name__}: {e}")
        return {segment_field_name: segment, "segment_index": idx, "k_chosen": k_chosen}

    return app
