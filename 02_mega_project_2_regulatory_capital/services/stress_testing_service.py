"""
Problem 4 — Macro Stress Testing — real deployable FastAPI service.

Applies the SAME real, documented, cited macro scenarios `pipeline_mp2_nb04.py`
evaluates (Section 5's `SCENARIOS` list, reproduced verbatim below so this
service and the notebook can never silently drift apart), via the SAME real
single-factor Vasicek conditional-PD-given-Z formula and the SAME
`basel_retail_capital_k()` function this suite already uses in
`regulatory_capital_features.py` and Problem 1's `capital_requirement_service.py`.
No new formula, no new assumption -- see module docstring of
`pipeline_mp2_nb04.py` for the full citation of each scenario's Z-value and
LGD multiplier.

Run locally:
    uvicorn stress_testing_service:app --host 0.0.0.0 --port 8006

Endpoints:
    GET  /health      -- liveness
    GET  /schema       -- the real, cited scenario definitions applied
    POST /score/{scenario} -- given real PD + applicant fields + EAD, returns
                              the real stressed PD, LGD, capital K, RWA, and
                              capital requirement for that one named scenario
                              ("Baseline", "Adverse", or "Severely Adverse")
"""
import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from scipy.stats import norm

THIS_DIR = Path(__file__).resolve().parent
MP2_DIR = THIS_DIR.parent
SUITE_ROOT = MP2_DIR.parent

sys.path.insert(0, str(SUITE_ROOT / "src"))
from features.regulatory_capital_features import (
    SEGMENT_DEFINITIONS, other_retail_correlation, basel_retail_capital_k,
)
from serving.auth_common import require_api_key

# Real, disclosed ASSUMPTION -- identical constants to pipeline_mp2_nb04.py
# Section 5. Kept in one place here so the notebook and this service can
# never silently drift apart.
SCENARIOS = {
    "Baseline": {"z_shock": 0.0, "lgd_multiplier": 1.0,
                 "description": "No shock -- the real, unmodified input PD/LGD."},
    "Adverse": {"z_shock": -1.6449, "lgd_multiplier": 1.0,
                "description": "Standard-normal 95th-percentile adverse value (Phi^-1(0.05) = -1.645, "
                                "a documented '1-in-20' downturn severity convention)."},
    "Severely Adverse": {"z_shock": -3.0902, "lgd_multiplier": 1.25,
                          "description": "Phi^-1(0.001) = -3.09 -- the SAME 99.9th-percentile severity "
                                          "Basel's own closed-form capital function is calibrated to, plus "
                                          "a documented 25% relative LGD downturn add-on (capped at 100%)."},
}


def _assign_segment(name_contract_type: str, flag_own_realty: str, flag_own_car: str) -> str:
    if name_contract_type == "Revolving loans":
        return "Revolving (QRRE)"
    if name_contract_type == "Cash loans" and flag_own_realty == "Y":
        return "Secured — Real Estate"
    if name_contract_type == "Cash loans" and flag_own_realty == "N" and flag_own_car == "Y":
        return "Secured — Other (Vehicle/Goods)"
    return "Unsecured — Other Retail"


class StressRequest(BaseModel):
    PD: float = Field(..., ge=0.0, le=1.0, description="Real, unstressed probability of default (0-1).")
    AMT_CREDIT: float = Field(..., gt=0.0, description="Real disbursed/approved credit amount (EAD proxy).")
    NAME_CONTRACT_TYPE: str = Field(..., description="Real Home Credit field: 'Cash loans' or 'Revolving loans'.")
    FLAG_OWN_REALTY: Optional[str] = Field(default="N")
    FLAG_OWN_CAR: Optional[str] = Field(default="N")


app = FastAPI(
    title="Home Credit — Macro Stress Testing (Problem 4)",
    description="Real, documented macro stress scenarios applied via the same Vasicek capital formula as Problem 1.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "scenarios": list(SCENARIOS.keys())}


@app.get("/schema", dependencies=[Depends(require_api_key)])
def schema():
    return {"scenarios": SCENARIOS}


@app.post("/score/{scenario}", dependencies=[Depends(require_api_key)])
def score(scenario: str, request: StressRequest):
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario}'. Choose one of: "
                                                      f"{list(SCENARIOS.keys())}")
    try:
        segment = _assign_segment(request.NAME_CONTRACT_TYPE, request.FLAG_OWN_REALTY or "N",
                                   request.FLAG_OWN_CAR or "N")
        seg_def = SEGMENT_DEFINITIONS[segment]
        base_lgd = seg_def["lgd"]
        scen = SCENARIOS[scenario]
        z = scen["z_shock"]

        r = seg_def["r_fixed"] if seg_def["correlation_mode"] == "fixed" else other_retail_correlation(request.PD)
        if scenario == "Baseline":
            stressed_pd = request.PD
        else:
            pd_clipped = min(max(request.PD, 1e-6), 1 - 1e-6)
            a = norm.ppf(pd_clipped) / (1 - r) ** 0.5
            b = (r / (1 - r)) ** 0.5
            stressed_pd = float(min(max(norm.cdf(a - b * z), 1e-6), 1 - 1e-6))
        stressed_lgd = min(base_lgd * scen["lgd_multiplier"], 1.0)

        k = basel_retail_capital_k(stressed_pd, stressed_lgd, r)
        ead = request.AMT_CREDIT
        el = stressed_pd * stressed_lgd * ead
        rwa = k * 12.5 * ead
        capital_requirement = rwa * 0.08
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Scoring failed: {type(e).__name__}: {e}")
    return {
        "scenario": scenario, "z_shock": z, "lgd_multiplier": scen["lgd_multiplier"],
        "capital_segment": segment, "unstressed_pd": request.PD, "stressed_pd": stressed_pd,
        "stressed_lgd": stressed_lgd, "correlation_r": r, "capital_k": k, "ead_proxy": ead,
        "expected_loss": el, "rwa": rwa, "capital_requirement": capital_requirement,
    }
