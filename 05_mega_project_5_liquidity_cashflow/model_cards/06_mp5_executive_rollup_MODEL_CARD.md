# Model Card — Problem 6: Mega Project 5 Executive Rollup

Notebook: `notebooks/06_mp5_executive_rollup.ipynb`
Outputs: `decision_engine/reports/notebook_06_*` (gitignored — regenerate
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

Pure consolidation of Problems 1-5's own real summaries into one
Mega-Project-level Word/Excel/HTML report, plus illustrative financial
impact and a 6-horizon ROI timeline. Not a model itself — no training, no
inference.

## Real, current results (from your own full run)

- **5/5 problems available and recommended for production; 0 need
  review, 0 not run** — `rollup_verdict = "ALL AVAILABLE PROBLEMS
  RECOMMENDED FOR PRODUCTION"`
- **4/4 cross-checks pass**: NB02↔NB03 90-day CFaR identity, NB02↔NB05
  relative-difference recomputation consistency, NB01↔NB05 collection-rate
  reasonableness, ROI timeline monotonically non-decreasing
- Total illustrative annual benefit: **$339,587** (avoided manual
  cashflow-reconciliation cost, $1.00/applicant × 339,587 real
  applicants) — the only monetized line; Problems 2, 3, 4, and 5 are
  reported as real cost-context figures (real dollar exposure/gap
  amounts), never added into the benefit total

## Note on Problem 5's disclosed REVIEW finding

This rollup counts Problem 5 as recommended because its structural
integrity checks (6/6) pass — the REVIEW verdict on its own model card is
a scenario-specific business finding at the Severely Adverse 90-day
horizon, not a pipeline failure. Both facts are true simultaneously and
are stated plainly in each problem's own model card; this rollup does not
paper over that finding, it simply doesn't treat a disclosed stress-test
result as equivalent to a broken pipeline.

## Verification status

Verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check.

## Limitations

- The financial-impact figures are illustrative, based on disclosed
  per-unit assumptions — not measured firm financials.
- Depends on all 5 problem notebooks having been run first, in order.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Notebooks 01-05 in order, then
   `notebooks/06_mp5_executive_rollup.ipynb`.
4. Real outputs are written to `decision_engine/reports/` (gitignored —
   regenerate locally).
