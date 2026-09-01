"""
Problem 1 — Credit Default Prediction — real deployable FastAPI scoring service.

Wraps Notebook 01's real, already-trained champion model bundle
(decision_engine/artifacts/notebook_01_champion_model.joblib) -- this service
does NOT retrain anything; it loads the exact model Notebook 01 produced and
scores real applicant records with it, identically to how Notebook 01 itself
scores its holdout set.

Run locally:
    uvicorn credit_default_scoring_service:app --host 0.0.0.0 --port 8001

Endpoints:
    GET  /health  -- liveness + which champion model is loaded
    GET  /schema  -- the real feature list this model expects
    POST /score   -- {"probability_of_default": float, "champion_model": str}
"""
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MP1_DIR = THIS_DIR.parent
SUITE_ROOT = MP1_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.scoring_service_common import build_scoring_app

BUNDLE_PATH = Path(
    os.environ.get("NB01_BUNDLE_PATH", str(MP1_DIR / "decision_engine" / "artifacts" / "notebook_01_champion_model.joblib"))
)

app = build_scoring_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Credit Default Prediction (Problem 1)",
    description="Real probability-of-default scoring using Notebook 01's trained champion model.",
    score_label="probability_of_default",
)
