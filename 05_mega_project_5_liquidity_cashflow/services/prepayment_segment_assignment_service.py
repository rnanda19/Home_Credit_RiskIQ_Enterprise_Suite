"""
Problem 4 — Prepayment / Early-Repayment Behavior Segmentation — real
deployable FastAPI service.

Wraps Notebook 04's real, already-fitted clustering bundle
(decision_engine/artifacts/notebook_04_segment_model.joblib) -- this
service does NOT retrain anything; it applies the exact real K-Means
model, the same real winsorize bounds, and the real fitted StandardScaler
Notebook 04 produced to a new real applicant's already-engineered
prepayment-conduct feature vector, exactly mirroring Mega Project 3's
segment-assignment services and Mega Project 4's Notebook 02 service --
all three share this same `src/serving/segment_assignment_common.py`
factory unchanged.

STATUS (2026-09-02): the notebook has not yet been re-run since this
persistence code was added, so no bundle exists on disk yet and this
service is unverified -- it will fail fast and loudly at startup
(`load_bundle()` raises) until `notebook_04_segment_model.joblib` exists.
See the Problem 4 model card for the current status.

Run locally:
    uvicorn prepayment_segment_assignment_service:app --host 0.0.0.0 --port 8015

Endpoints:
    GET  /health  -- liveness + how many real segments (k) are loaded
    GET  /schema  -- the real feature list + real winsorize bounds this model expects
    POST /score   -- {"prepayment_segment": str, "segment_index": int, "k_chosen": int}
"""
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MP5_DIR = THIS_DIR.parent
SUITE_ROOT = MP5_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.segment_assignment_common import build_segment_app

BUNDLE_PATH = Path(
    os.environ.get("NB04_SEGMENT_MODEL_PATH",
                    str(MP5_DIR / "decision_engine" / "artifacts" / "notebook_04_segment_model.joblib"))
)

app = build_segment_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Prepayment / Early-Repayment Behavior Segmentation (Problem 4)",
    description="Real prepayment-behavior segment assignment using Notebook 04's fitted, winsorized K-Means model.",
    segment_field_name="prepayment_segment",
    history_flag_note="Applicants with zero real prior loan-servicing history get 'No Payment History' "
                       "in the notebook's own population — this single-record API assumes the caller "
                       "already knows whether real payment history exists; it does not itself decide that.",
)
