"""
Problem 2 — Credit Bureau Behavioral Segmentation — real deployable FastAPI service.

Wraps Notebook 02's real, already-fitted clustering bundle
(decision_engine/artifacts/notebook_02_segment_model.joblib) -- this service
does NOT retrain anything; it applies the exact real K-Means model and real
fitted StandardScaler Notebook 02 produced to a new real applicant's
already-engineered bureau behavioral feature vector (see
`src/features/risk_segmentation_features.engineer_bureau_behavior_features()`
for how those real features are computed from real bureau.csv/
bureau_balance.csv rows).

Run locally:
    uvicorn bureau_segment_assignment_service:app --host 0.0.0.0 --port 8008

Endpoints:
    GET  /health  -- liveness + how many real segments (k) are loaded
    GET  /schema  -- the real feature list this model expects
    POST /score   -- {"bureau_segment": str, "segment_index": int, "k_chosen": int}
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
    os.environ.get("NB02_SEGMENT_MODEL_PATH",
                    str(MP3_DIR / "decision_engine" / "artifacts" / "notebook_02_segment_model.joblib"))
)

app = build_segment_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Credit Bureau Behavioral Segmentation (Problem 2)",
    description="Real bureau behavioral segment assignment using Notebook 02's fitted K-Means model.",
    segment_field_name="bureau_segment",
    history_flag_note="Applicants with zero real bureau history get 'No Bureau History' in the notebook's "
                       "own population — this single-record API assumes the caller already knows whether "
                       "real bureau history exists; it does not itself decide that.",
)
