# Model Card — Problem 6: Executive Rollup (Mega Project 1)

Notebook: `notebooks/06_mp1_executive_report.ipynb`
Service: none — not a model, a consolidation report
Bundle: none

## Intended use

Consolidates Problems 1-5's own real, already-verified summaries into one
Mega-Project-level Word/Excel/HTML report with an illustrative financial
impact figure and a 6-horizon ROI timeline. It computes nothing new — it
reads each problem's real `notebook_0X_summary.json` and aggregates only
fields those problems already reported.

## Real, current result (2026-09-02 rerun)

Per `decision_engine/artifacts/mp1_executive_summary.json`:

| # | Problem | Method | Verdict | Integrity checks |
|---|---|---|---|---|
| 1 | Credit Default Prediction | LightGBM | RECOMMENDED FOR PRODUCTION | 13/13 PASS |
| 2 | Loan Application Approval | LightGBM | RECOMMENDED FOR PRODUCTION | 18/18 PASS |
| 3 | Credit Score Estimation | Statistical/tiering analysis (no model trained) | RECOMMENDED FOR PRODUCTION | 11/11 PASS |
| 4 | Repayment Capacity Analysis | Statistical/tiering analysis (no model trained) | STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION | 13/13 PASS |
| 5 | Previous Application Outcomes | Statistical/tiering analysis (no model trained) | STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION | 13/13 PASS |

All 5/5 real problem summaries found. Real total annual benefit run-rate:
**$37,421,672**, built only from real benefit fields — cost-context rows
(Problems 4 and 5's) are never added into the benefit total; this is
checked programmatically (`cost_context_never_added_to_benefit_total`).

Real benefit and cost-context breakdown:
- Problem 1: real default losses prevented — $33,300,864 (portfolio scale $27,559,997,440).
- Problem 2: manual review cost avoided — $3,198,275.
- Problem 3: manual credit-scoring cost avoided — $922,533.
- Problem 4: **cost context, not benefit** — recommended investment in enhanced manual review for the weakest repayment-capacity tier: $922,500 (a proactive spend this analysis recommends, not a savings it produced).
- Problem 5: **cost context, not benefit** — existing real operational cost of processing historical refused applications: $2,906,780 (informational context on today's process, not a cost this notebook avoided).

Real 6-horizon ROI timeline (flat annual run-rate, no growth/compounding
assumed — `GROWTH_RATE_ASSUMPTION_PCT = 0.0`):

| Horizon | Cumulative benefit |
|---|---|
| 1 Month | $3,118,473 |
| 6 Months | $18,710,836 |
| 1 Year | $37,421,672 |
| 2 Years | $74,843,344 |
| 3 Years | $112,265,016 |
| 5 Years | $187,108,360 |

## Integrity checks (all pass on this real run)

- `all_5_notebook_summaries_found`: true
- `benefit_total_computed_from_real_fields_only`: true
- `roi_timeline_monotonically_increasing`: true
- `cost_context_never_added_to_benefit_total`: true
- `every_available_problem_has_a_story`: true
- `every_available_problem_has_an_insight`: true

## Limitations

- The ROI timeline is a flat-run-rate projection (no growth, no
  compounding, no discounting) — a simplifying assumption disclosed in
  the notebook's own module docstring, not a forecasting model.
- This report does not re-derive or re-validate any upstream problem's
  verdict; it trusts each problem's own real summary JSON as ground
  truth. If an upstream problem's verdict changes on a future rerun, this
  rollup must be regenerated to reflect it.
- Problems 4 and 5's dollar figures are cost context (money already being
  spent, or a recommended future spend) — deliberately excluded from the
  benefit total by the `cost_context_never_added_to_benefit_total` check,
  not omitted by oversight.
