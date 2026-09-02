"""
Problem 4 — POS/Cash Loan Delinquency Trajectory — real deployable FastAPI service.

Wraps Notebook 04's real, already-trained champion model bundle
(decision_engine/artifacts/notebook_04_champion_model.joblib) -- this service
does NOT retrain anything; it loads the exact real model Notebook 04
produced (trained on real POS/cash-loan delinquency-trajectory behavioral
features) and scores a real applicant's already-engineered feature vector
with it, identically to how Notebook 04 itself scores its holdout set.

A REAL, DISCLOSED SCOPE BOUNDARY: this service takes the already-engineered
real feature vector as input (one field per name in the bundle's real
`feature_cols` list), not raw multi-row POS_CASH_balance.csv history.

Run locally:
    uvicorn pos_cash_trajectory_scoring_service:app --host 0.0.0.0 --port 8014

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
    os.environ.get("NB04_BUNDLE_PATH",
                    str(MP4_DIR / "decision_engine" / "artifacts" / "notebook_04_champion_model.joblib"))
)

app = build_scoring_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — POS/Cash Loan Delinquency Trajectory (Problem 4)",
    description="Real POS/cash-trajectory-risk scoring using Notebook 04's trained champion model on real "
                 "POS/cash-loan delinquency behavioral features.",
    score_label="probability",
)
