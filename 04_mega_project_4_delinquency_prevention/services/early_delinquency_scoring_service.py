"""
Problem 1 — Early Delinquency Risk Scoring — real deployable FastAPI service.

Wraps Notebook 01's real, already-trained champion model bundle
(decision_engine/artifacts/notebook_01_champion_model.joblib) -- this service
does NOT retrain anything; it loads the exact real model Notebook 01
produced (trained on real installment-payment behavioral features, never a
re-derivation of Mega Project 1's application-time model -- see the
notebook's own module docstring for the full "why this is genuinely new"
disclosure) and scores a real applicant's already-engineered behavioral
feature vector with it, identically to how Notebook 01 itself scores its
holdout set.

A REAL, DISCLOSED SCOPE BOUNDARY (identical to Mega Project 3's own segment
services): this service takes the already-engineered real feature vector as
input (one field per name in the bundle's real `feature_cols` list, computed
by `src/features/delinquency_features.engineer_installment_behavior_features()`
from real installments_payments.csv rows), not the raw multi-row transaction
history itself.

Run locally:
    uvicorn early_delinquency_scoring_service:app --host 0.0.0.0 --port 8011

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
    os.environ.get("NB01_BUNDLE_PATH",
                    str(MP4_DIR / "decision_engine" / "artifacts" / "notebook_01_champion_model.joblib"))
)

app = build_scoring_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Early Delinquency Risk Scoring (Problem 1)",
    description="Real early-delinquency-risk scoring using Notebook 01's trained champion model on real "
                 "installment-payment behavioral features.",
    score_label="probability",
)
