# Model Card — Problem 1: Portfolio Cashflow Timing & Reliability

Notebook: `notebooks/01_portfolio_cashflow_timing_reliability.ipynb`
Outputs: `decision_engine/reports/notebook_01_*` (gitignored — regenerate
by running the notebook)

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## Intended use

A portfolio-level, real dollar-weighted view of cash inflow reliability —
every other notebook in this suite measures reliability by installment
*count* ("35% of installments were late"); this one weights every measure
by real dollar amount instead, and reconstructs a real, time-indexed,
calendar-period view of aggregate portfolio cash inflow. Reuses Mega
Project 1's real `REPAYMENT_CAPACITY_RATIO` formula directly.

## Not a per-applicant model — no deployable service

This is a portfolio/treasury-level aggregation, not a classifier or
clustering model — there is no per-applicant record to serve, so no
`.joblib` bundle and no FastAPI service exist for this problem, by design
(matching this suite's own precedent for population-level problems).

## Real, current results (from your own full run)

- **339,587 real applicants scored**, across **98 real calendar periods**
- Portfolio total scheduled cash: **$231,984,426,999**; total collected:
  **$234,482,862,800** — a real dollar collection rate of **101.08%**
  (above the 90% treasury benchmark)
- Capacity-quartile reliability holds monotonic within noise
- **8/8 structural integrity checks pass**

## Verification status

Verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check.

## Limitations

- Dollar collection rate above 100% reflects real overpayment/prepayment
  activity mixed into aggregate collections, not a measurement error —
  see Problem 4 for the applicant-level prepayment-conduct lens.
- No fairness/bias audit performed in this pass (not applicable — no
  per-applicant decision is made here).

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run `notebooks/01_portfolio_cashflow_timing_reliability.ipynb`
   end-to-end.
4. Real outputs are written to `decision_engine/reports/` (gitignored —
   regenerate locally).
