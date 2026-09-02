"""
Problem 3 — Revolving/Credit-Card Distress Early Warning — real deployable FastAPI service.

Wraps Notebook 03's real, already-trained champion model bundle
(decision_engine/artifacts/notebook_03_champion_model.joblib) -- this service
does NOT retrain anything; it loads the exact real model Notebook 03
produced (trained on real revolving/credit-card utilization and payment
behavioral features) and scores a real applicant's already-engineered
feature vector with it, identically to how Notebook 03 itself scores its
holdout set.

A REAL, DISCLOSED SCOPE BOUNDARY: this service takes the already-engineered
real feature vector as input (one field per name in the bundle's real
`feature_cols` list), not raw multi-row credit_card_balance.csv history.

Run locally:
    uvicorn revolving_distress_scoring_service:app --host 0.0.0.0 --port 8013

Endpoints:
    GET  /health  -- liveness + which champion model is loaded
    GET  /schema  -- the real feature list this model expects
    POST /score   -- {"probability": float, "champion_model": str, "top_reasons": [...]}
"""
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MP4_DIR = THIS_DIR.parent
SUITE_ROOT = MP4_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.scoring_service_common import build_scoring_app

BUNDLE_PATH = Path(
    os.environ.get("NB03_BUNDLE_PATH",
                    str(MP4_DIR / "decision_engine" / "artifacts" / "notebook_03_champion_model.joblib"))
)

app = build_scoring_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Revolving/Credit-Card Distress Early Warning (Problem 3)",
    description="Real revolving-distress-risk scoring using Notebook 03's trained champion model on real "
                 "credit-card utilization and payment behavioral features.",
    score_label="probability",
)
