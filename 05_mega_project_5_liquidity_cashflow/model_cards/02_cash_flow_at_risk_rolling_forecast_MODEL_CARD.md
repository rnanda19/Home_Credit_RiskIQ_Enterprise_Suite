# Model Card — Problem 2: Cash-Flow-at-Risk (CFaR) Rolling Forecast

Notebook: `notebooks/02_cash_flow_at_risk_rolling_forecast.ipynb`
Outputs: `decision_engine/reports/notebook_02_*` (gitignored — regenerate
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

A real, vectorized bootstrap Monte Carlo forecast of 30/60/90-day cash
inflow, resampled from Problem 1's own real historical collection rates —
never an assumed normal curve. Answers "how much of scheduled cash can we
actually count on collecting, at a given confidence level, over the next
N days."

## Not a per-applicant model — no deployable service

Portfolio-level forecast, not a per-applicant classifier — no `.joblib`
bundle and no FastAPI service, by design.

## Real, current results (from your own full run)

- **98 real historical periods** used as the resampling base;
  **20,000 Monte Carlo draws** per horizon
- 30-day: MC mean **$4,950,465,918** vs. closed-form **$4,953,553,762**
  (0.062% relative difference — reconciles)
- 60-day: MC mean **$9,908,863,716** vs. closed-form **$9,907,107,524**
  (0.018% relative difference — reconciles)
- 90-day: MC mean **$14,863,374,333** vs. closed-form **$14,860,661,286**
  (0.018% relative difference — reconciles)
- **8/8 structural integrity checks pass**, including percentile
  ordering at every horizon

## Verification status

Verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check.

## Limitations

- The 5th-percentile (`p5_cfar`) figure is the input Problem 3's own
  coverage-ratio calculation depends on directly — see that problem's own
  model card for how it's used.
- No fairness/bias audit performed in this pass (not applicable — no
  per-applicant decision is made here).

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run `notebooks/01_portfolio_cashflow_timing_reliability.ipynb` first
   (this notebook reuses its real historical periods), then
   `notebooks/02_cash_flow_at_risk_rolling_forecast.ipynb`.
4. Real outputs are written to `decision_engine/reports/` (gitignored —
   regenerate locally).
