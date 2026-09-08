# Adverse Action Notices

This document exists to close a real, previously-disclosed gap: "No
mechanism exists to translate a model's decision into the plain-English,
specific reasons a denied applicant is legally entitled to (ECOA/Reg B
'statement of specific reasons')."

## What exists

`src/serving/adverse_action_common.py`, wired as a new `POST
/adverse-action-notice` endpoint into `src/serving/scoring_service_common.py`'s
shared `build_scoring_app()` factory — so every classifier service this
factory builds gets the endpoint automatically (HYPER: built once, not
per-service).

The endpoint accepts the same real feature payload as `/score`, plus a
caller-supplied `threshold` (this suite makes no automated accept/reject
decision of its own — see `loan_approval_scoring_service.py`'s own
docstring — so the threshold that defines "adverse" has to come from the
caller). It reuses this suite's existing real occlusion-based
explainability path, `serving.explainability_common.top_reason_codes`, then
does two things that path does not do on its own:

1. **Translates real feature names into plain English.** A curated
   `REASON_CODE_MAP`, grounded in this suite's real 218 engineered feature
   names (`grep`-verified against `src/features/*.py` on 2026-09-08), covers
   the features most likely to actually rank as top reasons — requested-
   credit structure, income/employment, external bureau scores, bureau and
   installment repayment history, revolving utilization, and prior-
   application history. Anything not curated falls through to a mechanical
   abbreviation-expansion + title-case fallback (`_humanize_fallback`), so
   an unmapped feature never leaks a raw `ALL_CAPS_COLUMN_NAME` into
   customer-facing text — real, but lower quality than a curated entry.

2. **Structurally excludes protected-basis and fair-lending-proxy features
   from the customer-facing reason list.** ECOA explicitly forbids sex,
   marital status, and age as bases for a credit decision. This suite's
   real feature set includes exactly such fields (`CODE_GENDER`,
   `NAME_FAMILY_STATUS`, `DAYS_BIRTH`/`AGE_YEARS`), and separately includes
   two well-documented proxy-discrimination risks that mature fair-lending
   practice also keeps out of adverse-action letters even when a model
   technically used them: social-circle default history
   (`DEF_30_CNT_SOCIAL_CIRCLE`, `OBS_30_CNT_SOCIAL_CIRCLE` — a real
   guilt-by-association signal) and coarse geography
   (`REGION_RATING_CLIENT`, `REGION_POPULATION_RELATIVE` — a real redlining
   proxy). If any of these rank among the real top contributing factors for
   a given decision, `render_adverse_action_notice()` removes them from
   `principal_reasons` and instead reports them in a separate
   `suppressed_factors` list (with a `protected_basis` or
   `fair_lending_proxy` category), so the fact that the model leaned on one
   of these fields is visible for fair-lending review rather than silently
   dropped.

## What this does *not* do

This is a wording/disclosure safeguard on the output of a model that has
already scored an application — it structurally prevents a specific reason
of "your gender" or "your neighborhood" from reaching a customer, and
surfaces when that would have happened. It does **not** audit whether the
underlying model itself produces a disparate impact across protected
groups. That is the separate, permanently-open fair-lending/bias-audit gap
this repo's remediation tracker documents as a real, structural "No" — no
demographic labels exist anywhere in this suite's real feature pipeline to
run such an audit against, synthetic or real. This module makes the
adverse-action *notice* honest; it does not and cannot make that separate,
larger claim.

In a real production deployment, `suppressed_factors` would be routed to an
internal fair-lending review queue behind its own auth scope, not returned
in the same response as the customer notice — it is returned here, openly,
so the suppression behavior itself is directly testable and verifiable in
this portfolio artifact, which is a real, disclosed scope difference from
how this would ship in production.

## Real, disclosed scope limits

- `REASON_CODE_MAP` is hand-curated, not exhaustive across all 218 real
  feature names — see `_humanize_fallback()`'s mechanical fallback above.
- `adverse_direction` ("positive" for default-probability/risk-style
  scores, "negative" for approval-probability-style scores) is derived
  once from `score_label` via a simple substring check
  (`"approval" in score_label.lower()`), not a per-service configuration
  flag — correct for every service in this suite today, but a service
  whose `score_label` doesn't fit that convention would need an explicit
  override, which this factory does not yet expose.
- Tested with a real, freshly fitted `LogisticRegression` bundle (see
  `src/tests/test_adverse_action_endpoint.py`), not yet exercised against a
  real trained bundle from this suite's own notebooks on real Kaggle data —
  same disclosed scope limit as this suite's other new hardening work this
  session (drift monitoring, rate limiting, load testing).

## Example

```
POST /adverse-action-notice
{
  "AMT_CREDIT": 500000,
  "AMT_INCOME_TOTAL": 90000,
  "EXT_SOURCE_1": 0.12,
  ...
  "threshold": 0.5
}
```

```json
{
  "champion_model": "lightgbm_v3",
  "decision": "adverse_action",
  "score": 0.71,
  "threshold": 0.5,
  "principal_reasons": [
    {"factor": "CREDIT_TO_INCOME_RATIO", "reason": "Amount of credit requested relative to income", "contribution": 0.18},
    {"factor": "EXT_SOURCE_1", "reason": "External credit bureau score (source 1)", "contribution": 0.11}
  ],
  "suppressed_factors": [
    {"factor": "REGION_RATING_CLIENT", "category": "fair_lending_proxy"}
  ]
}
```
