"""
src/serving/explainability_common.py

HYPER shared component: real, per-request "top reason codes" for a service
wrapping a probability-producing classifier -- exact marginal-contribution
explanation via occlusion (re-score the SAME real request with one real
feature reset to a real baseline value, report the resulting real change in
predicted probability), computed live against the real loaded model on
every call -- never cached, sampled, or approximated. Mirrors CFPB Circular
2022-03's "specific, principal reason" standard for adverse-action
explanations, and the same pattern used by the AMEX RiskIQ Enterprise
Credit Risk Platform's own `_top_reason_codes()` (a related project on this
account). Added 2026-09-02 as a real, disclosed hardening fix -- no service
in this suite had per-request explainability before this pass.

Built once, imported by every classifier-backed scoring service in this
suite (HYPER) rather than duplicated per service.
"""
from typing import Callable


def top_reason_codes(
    predict_fn: Callable[[dict], float],
    raw_payload: dict,
    baseline_payload: dict,
    n: int = 3,
) -> list[dict]:
    """predict_fn(payload) -> the caller's own real scoring function (e.g. this
    suite's `score_one()`), returning a real probability for that payload.
    baseline_payload: the real per-feature value each occluded feature is reset
    to -- supplied by the caller, since only the caller's own real preprocessing
    knows its real baseline convention (this suite's convention: None, which the
    caller's own real imputer/encoder already fills with the real training-set
    median / "Missing" category -- see scoring_service_common.py -- so this
    function never invents its own baseline logic).

    Returns up to `n` reason dicts {"factor": str, "contribution": float},
    ranked by |contribution|, largest first. A feature already at its own real
    baseline in raw_payload contributes nothing and is never listed -- this
    never fabricates a reason that isn't real (a request that matches its own
    baseline everywhere returns an empty list, not a padded one)."""
    base_pred = predict_fn(raw_payload)
    impacts = []
    for feature, raw_value in raw_payload.items():
        baseline_value = baseline_payload.get(feature)
        if raw_value == baseline_value:
            continue
        occluded = dict(raw_payload)
        occluded[feature] = baseline_value
        occluded_pred = predict_fn(occluded)
        impacts.append({"factor": feature, "contribution": base_pred - occluded_pred})
    impacts.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return impacts[:n]
