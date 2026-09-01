"""
Problem 3 — Repayment Behavior Segmentation — real deployable FastAPI service.

Wraps Notebook 03's real, already-fitted clustering bundle
(decision_engine/artifacts/notebook_03_segment_model.joblib) -- this service
does NOT retrain anything; it applies the exact real K-Means model, the same
real winsorize bounds, and the real fitted StandardScaler Notebook 03
produced to a new real applicant's already-engineered repayment-conduct
feature vector (see `src/features/risk_segmentation_features.
engineer_repayment_behavior_features()` for how those real features are
computed from real installments_payments.csv/POS_CASH_balance.csv rows).

Run locally:
    uvicorn repayment_segment_assignment_service:app --host 0.0.0.0 --port 8009

Endpoints:
    GET  /health  -- liveness + how many real segments (k) are loaded
    GET  /schema  -- the real feature list + real winsorize bounds this model expects
    POST /score   -- {"repayment_segment": str, "segment_index": int, "k_chosen": int}
"""
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MP3_DIR = THIS_DIR.parent
SUITE_ROOT = MP3_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.segment_assignment_common import build_segment_app

BUNDLE_PATH = Path(
    os.environ.get("NB03_SEGMENT_MODEL_PATH",
                    str(MP3_DIR / "decision_engine" / "artifacts" / "notebook_03_segment_model.joblib"))
)

app = build_segment_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Repayment Behavior Segmentation (Problem 3)",
    description="Real repayment-behavior segment assignment using Notebook 03's fitted, winsorized K-Means model.",
    segment_field_name="repayment_segment",
    history_flag_note="Applicants with zero real previous-loan repayment history get 'No Repayment History' "
                       "in the notebook's own population — this single-record API assumes the caller "
                       "already knows whether real repayment history exists; it does not itself decide that.",
)
