"""
Problem 1 — Data-Driven Risk Tier Construction — real deployable FastAPI service.

Wraps Notebook 01's real, already-computed tier boundaries
(`decision_engine/artifacts/notebook_01_summary.json` ->
`tiering_config.tier_bin_edges`) -- the exact real CART-derived thresholds
Notebook 01's own `pd.cut(PD_ARRAY, bins=TIER_BIN_EDGES, ...)` call produces.
This service does NOT retrain the decision tree; it applies the SAME real,
already-fitted boundaries to a new real PD value, identically to how
Notebook 01 assigns a tier to its own scored population.

PD itself is a real input to this endpoint -- chain Mega Project 1's real
`credit_default_scoring_service` output into this service for a fully real,
end-to-end PD -> risk-tier pipeline.

Run locally:
    uvicorn risk_tier_assignment_service:app --host 0.0.0.0 --port 8007

Endpoints:
    GET  /health   -- liveness + how many real tiers are loaded
    GET  /schema   -- the real tier boundaries this service applies
    POST /score    -- {"PD": float} -> {"risk_tier": str, "tier_index": int}
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

THIS_DIR = Path(__file__).resolve().parent
MP3_DIR = THIS_DIR.parent

SUMMARY_PATH = Path(
    os.environ.get("NB01_SUMMARY_PATH",
                    str(MP3_DIR / "decision_engine" / "artifacts" / "notebook_01_summary.json"))
)
if not SUMMARY_PATH.exists():
    raise FileNotFoundError(
        f"Notebook 01's real summary not found at {SUMMARY_PATH}. Run "
        "03_mega_project_3_risk_segmentation/notebooks/01_data_driven_risk_tier_construction.ipynb "
        "end-to-end at least once before starting this service."
    )
with open(SUMMARY_PATH) as f:
    _summary = json.load(f)

_raw_edges = _summary["tiering_config"]["tier_bin_edges"]
# Real edges as saved: None marks the two non-finite boundaries pd.cut() used
# (Notebook 01 substitutes None for +/-inf before JSON serialization -- inf
# is not valid JSON). Reconstructed here exactly as pd.cut() needs them.
TIER_BIN_EDGES = [float("-inf") if i == 0 and e is None else
                  (float("inf") if i == len(_raw_edges) - 1 and e is None else e)
                  for i, e in enumerate(_raw_edges)]
N_TIERS = len(TIER_BIN_EDGES) - 1
TIER_LABELS = [f"Tier {i + 1}" for i in range(N_TIERS)]


def _assign_tier(pd_value: float) -> tuple[str, int]:
    """Identical semantics to `pd.cut(..., bins=TIER_BIN_EDGES, include_lowest=True)`:
    right-closed intervals, i.e. tier i covers (edge[i], edge[i+1]], except the
    first interval also includes its left edge."""
    for i in range(N_TIERS):
        lo, hi = TIER_BIN_EDGES[i], TIER_BIN_EDGES[i + 1]
        if (i == 0 and lo <= pd_value <= hi) or (i > 0 and lo < pd_value <= hi):
            return TIER_LABELS[i], i
    raise ValueError(f"Real PD {pd_value} falls outside every real tier boundary "
                      f"{TIER_BIN_EDGES} -- this should be unreachable for a PD in [0, 1].")


class RiskTierRequest(BaseModel):
    PD: float = Field(..., ge=0.0, le=1.0, description="Real probability of default (0-1) -- from "
                                                         "Mega Project 1's real champion model.")


app = FastAPI(
    title="Home Credit — Data-Driven Risk Tier Assignment (Problem 1)",
    description="Real tier assignment using Notebook 01's real, CART-derived tier boundaries.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "n_real_tiers": N_TIERS}


@app.get("/schema")
def schema():
    return {"tier_labels": TIER_LABELS, "tier_bin_edges": [None if not (-1e300 < e < 1e300) else e
                                                             for e in TIER_BIN_EDGES]}


@app.post("/score")
def score(request: RiskTierRequest):
    try:
        tier, idx = _assign_tier(request.PD)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Tier assignment failed: {type(e).__name__}: {e}")
    return {"risk_tier": tier, "tier_index": idx, "n_real_tiers": N_TIERS}
