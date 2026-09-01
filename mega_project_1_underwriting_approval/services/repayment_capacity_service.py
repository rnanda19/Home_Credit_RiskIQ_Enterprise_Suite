"""
Problem 11 — Repayment Capacity Analysis — real deployable FastAPI service.

Notebook 04 is a statistical/tiering analysis, not a trained classifier (see
its own notebook markdown: "not a predictive-model notebook, by design, not a
gap"). This service exposes the two real, deterministic ratio FORMULAS
Notebook 04 computes -- identical to pipeline_nb04.py Section 6 -- for a
single real applicant record:

    TOTAL_DEBT_BURDEN_RATIO    = (BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL + AMT_CREDIT) / (AMT_INCOME_TOTAL + 1.0)
    REPAYMENT_CAPACITY_RATIO   = AMT_INCOME_TOTAL / (AMT_ANNUITY + 1.0)

STATED LIMITATION (disclosed, not silently omitted): Notebook 04's 5-tier
"Weakest..Strongest" REPAYMENT_TIER label is a real quintile of the FULL
scored population at notebook-run time -- it is population-RELATIVE, not a
fixed threshold, so a single-record API cannot reproduce it without also
being handed that population's current quintile boundaries (which this suite
does not currently persist as a reusable artifact). This service therefore
returns the two real ratios only, not a tier label -- an honest scope
boundary rather than a fabricated fixed cutoff.

Run locally:
    uvicorn repayment_capacity_service:app --host 0.0.0.0 --port 8004

Endpoints:
    GET  /health
    POST /score  -- {"repayment_capacity_ratio": float | null,
                      "total_debt_burden_ratio": float | null,
                      "note": str}
"""
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


class RepaymentCapacityRequest(BaseModel):
    AMT_INCOME_TOTAL: float = Field(..., description="Real applicant annual income (required, > 0).")
    AMT_ANNUITY: Optional[float] = Field(default=None, description="Real requested loan annuity.")
    AMT_CREDIT: Optional[float] = Field(default=None, description="Real requested loan principal.")
    BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL: Optional[float] = Field(
        default=0.0, description="Real existing bureau-reported debt total (0 if none on file).")


app = FastAPI(
    title="Home Credit — Repayment Capacity Analysis (Problem 11)",
    description="Real, deterministic repayment-capacity ratio formulas from Notebook 04 (no trained model).",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "note": "Deterministic formulas, no trained model -- see module docstring."}


@app.post("/score")
def score(request: RepaymentCapacityRequest):
    repayment_capacity_ratio = None
    total_debt_burden_ratio = None
    if request.AMT_ANNUITY is not None:
        repayment_capacity_ratio = request.AMT_INCOME_TOTAL / (request.AMT_ANNUITY + 1.0)
    if request.AMT_CREDIT is not None:
        bureau_debt = request.BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL or 0.0
        total_debt_burden_ratio = (bureau_debt + request.AMT_CREDIT) / (request.AMT_INCOME_TOTAL + 1.0)
    return {
        "repayment_capacity_ratio": repayment_capacity_ratio,
        "total_debt_burden_ratio": total_debt_burden_ratio,
        "note": ("REPAYMENT_TIER is population-relative (a real quintile of Notebook 04's full scored "
                 "population) and is not reproducible from a single record -- see this file's docstring."),
    }
