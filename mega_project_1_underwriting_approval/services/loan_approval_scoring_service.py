"""
Problem 3 — Loan Application Approval — real deployable FastAPI scoring service.

Wraps Notebook 02's real, already-trained champion model bundle
(decision_engine/artifacts/notebook_02_champion_model.joblib). If Notebook 02
was run with Notebook 01's model already present, this bundle's real feature
list includes UPSTREAM_PD_FROM_NB01 (Notebook 01's real PD as a genuine input
feature) -- this service does not care either way; it simply scores with
whatever real feature list the loaded bundle actually declares (checked via
GET /schema), exactly like Notebook 02 itself does.

Run locally:
    uvicorn loan_approval_scoring_service:app --host 0.0.0.0 --port 8002

Endpoints:
    GET  /health  -- liveness + which champion model is loaded
    GET  /schema  -- the real feature list this model expects (includes
                     UPSTREAM_PD_FROM_NB01 only if Notebook 02 was run with it)
    POST /score   -- {"approval_probability": float, "champion_model": str}
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
    os.environ.get("NB02_BUNDLE_PATH", str(MP1_DIR / "decision_engine" / "artifacts" / "notebook_02_champion_model.joblib"))
)

app = build_scoring_app(
    bundle_path=BUNDLE_PATH,
    title="Home Credit — Loan Application Approval (Problem 3)",
    description="Real loan-approval-probability scoring using Notebook 02's trained champion model.",
    score_label="approval_probability",
)
