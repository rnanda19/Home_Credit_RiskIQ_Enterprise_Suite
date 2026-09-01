"""
Problem 4 — Revolving Credit Utilization Segmentation — real deployable FastAPI service.

Wraps Notebook 04's real, already-fitted clustering bundle
(decision_engine/artifacts/notebook_04_segment_model.joblib) -- this service
does NOT retrain anything; it applies the exact real K-Means model, the same
real winsorize bounds, and the real fitted StandardScaler Notebook 04
produced to a new real applicant's already-engineered revolving-credit
utilization feature vector (see `src/features/risk_segmentation_features.
engineer_revolving_credit_utilization_features()` for how those real
features are computed from real credit_card_balance.csv rows).

Run locally:
    uvicorn utilization_segment_assignment_service:app --host 0.0.0.0 --port 8010

Endpoints:
    GET  /health  -- liveness + how many real segments (k) are loaded
    GET  /schema  -- the real feature list + real winsorize bounds this model expects
    POST /score   -- {"utilization_segment": str, "segment_index": int, "k_chosen": int}
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
    os.environ.get("NB04_SEGMENT_MODEL_PATH",
                    str(MP3_DIR / "decision_engine" / "artifacts" / "notebook_04_segment_model.joblib"))
)

app = build_segment_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Revolving Credit Utilization Segmentation (Problem 4)",
    description="Real utilization segment assignment using Notebook 04's fitted, winsorized K-Means model.",
    segment_field_name="utilization_segment",
    history_flag_note="Applicants with zero real previous-loan revolving-credit history get 'No Revolving "
                       "Credit History' in the notebook's own population — this single-record API assumes "
                       "the caller already knows whether real revolving history exists; it does not itself "
                       "decide that.",
)
