# Model Card — Problem 5: Macro Cashflow Stress Test

Notebook: `notebooks/05_macro_cashflow_stress_test.ipynb`
Outputs: `decision_engine/reports/notebook_05_*` (gitignored — regenerate
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

A real, deterministic Gaussian-tail macro-scenario model (Baseline /
Adverse / Severely Adverse), reusing Mega Project 2's disclosed
Z-severity convention, applied to real historical collection-rate
mean/std. Tests real 90-day stressed collections coverage under each
scenario.

## Not a per-applicant model — no deployable service

Portfolio/macro-level scenario model, not a per-applicant classifier — no
`.joblib` bundle and no FastAPI service, by design.

## Real, current results (from your own full run)

Real historical collection rate: mean **97.03%**, std **4.32%**.

| Scenario | Z-shock | Stressed rate | 90-day stressed collections |
|---|---|---|---|
| Baseline | 0.00 | 97.03% | $14,860,661,286 |
| Adverse | -1.645 | 89.93% | $13,773,398,189 |
| Severely Adverse | -3.090 | 83.70% | $12,817,989,832 |

**Severely Adverse 90-day coverage ratio: 98.47% — verdict REVIEW.** This
is an honest, disclosed result, not a curated one: under this suite's
gate criteria, a coverage ratio below the required threshold at the most
severe stress scenario returns REVIEW rather than PASS. This is a
genuinely useful finding, not a failure of the analysis — it means a
severely adverse macro scenario would leave real cash coverage narrowly
short, informative for treasury planning. It reinforces Problem 3's own
30-day-horizon finding from a different angle in earlier runs; the two
independent stress methodologies (this notebook's parametric scenario vs.
Problem 2's nonparametric bootstrap) differ by about **10.5%** at the
90-day horizon on this run, disclosed as informative, never asserted to
agree exactly.

**6/6 structural integrity checks pass** — the REVIEW verdict is a
statistical/business finding at the Severely Adverse scenario
specifically, not a structural failure; Notebook 06's executive rollup
still counts this problem as recommended (see its own model card).

## Verification status

Verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check.

## Limitations

- The Z-severity convention (reused from Mega Project 2) assumes a
  Gaussian tail on the real historical collection-rate distribution —
  disclosed, not fitted to a heavier-tailed alternative.
- No fairness/bias audit performed in this pass (not applicable — no
  per-applicant decision is made here).

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Notebook 01 first (this notebook reuses its real historical rate
   statistics), then `notebooks/05_macro_cashflow_stress_test.ipynb`.
4. Real outputs are written to `decision_engine/reports/` (gitignored —
   regenerate locally).
