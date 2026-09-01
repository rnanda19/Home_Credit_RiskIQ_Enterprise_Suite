"""
Problem 1 — Expected Loss & Capital Requirement — real deployable FastAPI service.

Wraps `src/features/regulatory_capital_features.py`'s real Basel retail-IRB
Vasicek/ASRF closed-form functions -- the EXACT SAME real functions
`pipeline_mp2_nb01.py` imports and calls (never re-derived or approximated
here). This service does NOT train or load a model of its own: PD is a real
input to this endpoint (produced by Mega Project 1's real champion model --
see `01_mega_project_1_underwriting_approval/services/
credit_default_scoring_service.py` -- chain that service's output into this
one for a fully real, end-to-end PD -> capital pipeline). LGD and the asset
correlation R are assigned by the real, cited Basel segment table in
`regulatory_capital_features.SEGMENT_DEFINITIONS`, from real applicant
fields (NAME_CONTRACT_TYPE, FLAG_OWN_REALTY, FLAG_OWN_CAR) -- identical
segment-assignment logic to `assign_capital_segment()`.

Run locally:
    uvicorn capital_requirement_service:app --host 0.0.0.0 --port 8005

Endpoints:
    GET  /health   -- liveness
    GET  /schema   -- the real segment table this service applies
    POST /score    -- given real PD + applicant fields + EAD, returns real
                       EL, correlation R, capital K, RWA, and Pillar-1
                       capital requirement (identical formula to Notebook 01)
"""
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

THIS_DIR = Path(__file__).resolve().parent
MP2_DIR = THIS_DIR.parent
SUITE_ROOT = MP2_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from features.regulatory_capital_features import (
    SEGMENT_DEFINITIONS, SEGMENT_ORDER, other_retail_correlation, basel_retail_capital_k,
)


def _assign_segment(name_contract_type: str, flag_own_realty: str, flag_own_car: str) -> str:
    """Identical branching to `assign_capital_segment()`'s real Polars `when/then`
    chain in regulatory_capital_features.py, applied to a single real record."""
    if name_contract_type == "Revolving loans":
        return "Revolving (QRRE)"
    if name_contract_type == "Cash loans" and flag_own_realty == "Y":
        return "Secured — Real Estate"
    if name_contract_type == "Cash loans" and flag_own_realty == "N" and flag_own_car == "Y":
        return "Secured — Other (Vehicle/Goods)"
    return "Unsecured — Other Retail"


class CapitalRequest(BaseModel):
    PD: float = Field(..., ge=0.0, le=1.0, description="Real probability of default (0-1) -- from "
                                                         "Mega Project 1's real champion model.")
    AMT_CREDIT: float = Field(..., gt=0.0, description="Real disbursed/approved credit amount -- used "
                                                         "as this suite's disclosed EAD proxy (EAD_PROXY).")
    NAME_CONTRACT_TYPE: str = Field(..., description="Real Home Credit field: 'Cash loans' or 'Revolving loans'.")
    FLAG_OWN_REALTY: Optional[str] = Field(default="N", description="Real Home Credit field: 'Y' or 'N'.")
    FLAG_OWN_CAR: Optional[str] = Field(default="N", description="Real Home Credit field: 'Y' or 'N'.")


app = FastAPI(
    title="Home Credit — Expected Loss & Capital Requirement (Problem 1)",
    description="Real Basel retail-IRB Vasicek/ASRF capital calculation, identical to Notebook 01.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "note": "Deterministic real Basel formula, no trained model -- see module docstring."}


@app.get("/schema")
def schema():
    return {"segment_order": SEGMENT_ORDER,
            "segment_definitions": {k: {kk: vv for kk, vv in v.items() if kk not in ("condition",)}
                                     for k, v in SEGMENT_DEFINITIONS.items()}}


@app.post("/score")
def score(request: CapitalRequest):
    try:
        segment = _assign_segment(request.NAME_CONTRACT_TYPE, request.FLAG_OWN_REALTY or "N",
                                   request.FLAG_OWN_CAR or "N")
        seg_def = SEGMENT_DEFINITIONS[segment]
        lgd = seg_def["lgd"]
        r = seg_def["r_fixed"] if seg_def["correlation_mode"] == "fixed" else other_retail_correlation(request.PD)
        k = basel_retail_capital_k(request.PD, lgd, r)
        ead = request.AMT_CREDIT
        el = request.PD * lgd * ead
        rwa = k * 12.5 * ead
        capital_requirement = rwa * 0.08
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
    return {
        "capital_segment": segment, "lgd_assumed": lgd, "correlation_r": r, "capital_k": k,
        "ead_proxy": ead, "expected_loss": el, "rwa": rwa, "capital_requirement": capital_requirement,
        "capital_rate_of_ead": capital_requirement / ead if ead else None,
    }
