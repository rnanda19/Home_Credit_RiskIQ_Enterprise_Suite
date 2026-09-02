"""
Problem 2 — Installment Payment Behavior Detection — real deployable FastAPI service.

Wraps Notebook 02's real, already-fitted clustering bundle
(decision_engine/artifacts/notebook_02_kmeans_model.joblib) -- this service
does NOT retrain anything; it applies the exact real K-Means model and real
fitted StandardScaler Notebook 02 produced to a new real applicant's
already-engineered installment-payment behavioral feature vector (see
`src/features/delinquency_features.engineer_installment_behavior_features()`
for how those real features are computed from real installments_payments.csv
rows).

A REAL, DISCLOSED SCOPE BOUNDARY (identical to Mega Project 3's own segment
services): this service takes the already-engineered real feature vector as
input, not raw multi-row transaction history. Notebook 02's own bundle
carries no winsorize step (unlike Mega Project 3's Notebooks 03/04), so
`distance_to_each_segment` below is computed directly on the scaled real
feature vector, identically to the notebook.

Run locally:
    uvicorn payment_pattern_assignment_service:app --host 0.0.0.0 --port 8012

Endpoints:
    GET  /health  -- liveness + how many real patterns (k) are loaded
    GET  /schema  -- the real feature list this model expects
    POST /score   -- {"payment_pattern": str, "segment_index": int, "k_chosen": int,
                       "distance_to_each_segment": [...]}
"""
import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MP4_DIR = THIS_DIR.parent
SUITE_ROOT = MP4_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from serving.segment_assignment_common import build_segment_app

BUNDLE_PATH = Path(
    os.environ.get("NB02_KMEANS_MODEL_PATH",
                    str(MP4_DIR / "decision_engine" / "artifacts" / "notebook_02_kmeans_model.joblib"))
)

app = build_segment_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Installment Payment Behavior Detection (Problem 2)",
    description="Real payment-pattern assignment using Notebook 02's fitted K-Means model on real "
                 "installment-payment behavioral features.",
    segment_field_name="payment_pattern",
    history_flag_note="Applicants with zero real installment history have no behavioral signal to cluster "
                       "-- this single-record API assumes the caller already knows real installment "
                       "history exists; it does not itself decide that (identical scope boundary to "
                       "Notebook 01's own scoring service).",
)
