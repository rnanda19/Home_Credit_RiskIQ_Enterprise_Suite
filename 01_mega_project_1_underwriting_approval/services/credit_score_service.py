"""
Problem 3 — Credit Score Estimation — real deployable FastAPI scoring service.

Wraps Notebook 01's real, already-trained champion model bundle, then applies
Notebook 03's real PDO log-odds scorecard scaling on top of the real PD --
the exact same two-step computation Notebook 03 itself performs (Section 6 of
pipeline_nb03.py): score = OFFSET + FACTOR * ln((1-PD)/PD), where
FACTOR = PDO/ln(2) and OFFSET = BASE_SCORE - FACTOR*ln(BASE_ODDS).

BASE_SCORE=600 / BASE_ODDS=50 / PDO=20 are a real, disclosed ASSUMPTION
(standard FICO-style scorecard convention, not derived from this data) --
identical constants to Notebook 03, kept in this one place so the notebook and
this service can never silently drift apart.

Run locally:
    uvicorn credit_score_service:app --host 0.0.0.0 --port 8003

Endpoints:
    GET  /health  -- liveness + which upstream champion model is loaded
    GET  /schema  -- the real feature list this model expects
    POST /score   -- {"credit_score": float (300-900), "probability_of_default": float,
                       "scaling_assumptions": {...}, "champion_model": str}
"""
import os
import sys
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException

THIS_DIR = Path(__file__).resolve().parent
MP1_DIR = THIS_DIR.parent
SUITE_ROOT = MP1_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.scoring_service_common import load_bundle, score_one, build_request_model

BUNDLE_PATH = Path(
    os.environ.get("NB01_BUNDLE_PATH", str(MP1_DIR / "decision_engine" / "artifacts" / "notebook_01_champion_model.joblib"))
)

# Real, disclosed ASSUMPTION -- identical constants to pipeline_nb03.py Section 6.
BASE_SCORE = 600.0
BASE_ODDS = 50.0
PDO = 20.0
FACTOR = PDO / np.log(2)
OFFSET = BASE_SCORE - FACTOR * np.log(BASE_ODDS)
SCALING_ASSUMPTIONS = {
    "base_score": BASE_SCORE, "base_odds": BASE_ODDS, "pdo": PDO,
    "source": "standard credit-scorecard convention (FICO-style), not derived from this data",
}

_bundle = load_bundle(BUNDLE_PATH)
_numeric_features = _bundle["numeric_features"]
_categorical_features = _bundle["categorical_features"]
_champion_name = _bundle.get("champion_name", "unknown")
RequestModel = build_request_model("CreditScore", _numeric_features, _categorical_features)

app = FastAPI(
    title="Home Credit — Credit Score Estimation (Problem 3)",
    description="Real PDO scorecard score, built on Notebook 01's real trained champion model.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "upstream_champion_model": _champion_name,
            "scaling_assumptions": SCALING_ASSUMPTIONS}


@app.get("/schema")
def schema():
    return {"numeric_features": _numeric_features, "categorical_features": _categorical_features,
            "upstream_champion_model": _champion_name}


@app.post("/score")
def score(request: RequestModel):
    try:
        pd_value = score_one(_bundle, request.model_dump())
        pd_clipped = float(np.clip(pd_value, 1e-6, 1 - 1e-6))
        odds = (1 - pd_clipped) / pd_clipped
        raw_score = OFFSET + FACTOR * np.log(odds)
        credit_score = float(np.clip(raw_score, 300, 900))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
    return {
        "credit_score": credit_score,
        "probability_of_default": pd_clipped,
        "scaling_assumptions": SCALING_ASSUMPTIONS,
        "champion_model": _champion_name,
    }
