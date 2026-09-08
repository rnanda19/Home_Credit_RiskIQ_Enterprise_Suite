# Model Card — Problem 4: Prepayment / Early-Repayment Behavior Segmentation

Notebook: `notebooks/04_prepayment_early_repayment_segmentation.ipynb`
Outputs: `decision_engine/reports/notebook_04_*`,
`decision_engine/artifacts/notebook_04_segment_model.joblib` (gitignored —
regenerate by running the notebook)

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

Segments applicants by prepayment/early-repayment conduct — does this
applicant have a habit of paying early or overpaying — a behaviorally
distinct axis from Problems 1-3's dollar-collection-reliability lens.

## Real, unsupervised clustering — never trained against TARGET

A real K-Means model is fit over a real prepayment/early-payment feature
set, grouping applicants by prepayment-conduct similarity alone — never
trained against real `TARGET`. Real `TARGET` is used only afterward, as
an independent cross-check of whether the discovered segments carry any
real association with default.

## Real, current results (from your own full run)

- **Data-driven K = 3** segments chosen; silhouette score **0.383**
- **291,635 applicants (94.8%)** have real payment history and were
  clustered; the rest are the notebook's own explicit "No Payment
  History" segment, never imputed
- Cramer's V vs. real `TARGET`: **0.0312** (95% CI: 0.0284–0.0345)
- **7/7 structural integrity checks pass**, including the real
  `N_PAID_INSTALMENTS` reconciliation to raw valid rows

## Real `.joblib` persistence code + service — verified (2026-09-08)

Notebook 04's persistence code has now been run for real: the notebook
was re-executed end-to-end on the real, full-scale Home Credit dataset
and saved `{kmeans, scaler, feature_names, segment_labels, k_chosen,
random_seed, winsorize_report}` to
`decision_engine/artifacts/notebook_04_segment_model.joblib` (real file,
1.17MB, real k=3 KMeans, real fitted StandardScaler over 8 real
features). The real FastAPI service
(`services/prepayment_segment_assignment_service.py`, port 8015), built
on the shared `src/serving/segment_assignment_common.py` factory, was
then verified against that real bundle three ways: (1) the existing
`tests/test_scoring_services.py` check — the service's `/score` output
for a real applicant already present in the notebook's own real output
CSV was confirmed to exactly match the notebook's own real segment
assignment ("Prepayment Segment B"); (2) a real live end-to-end check —
the service launched as a real OS subprocess, its real `/health` and
`/score` endpoints hit over real HTTP, reproducing the same real match;
(3) `05_mega_project_5_liquidity_cashflow/tests/test_e2e_live_service.py`
(new) — a permanent, CI-safe real-subprocess/real-HTTP test using the
suite's standard synthetic fixture bundle, following the same
`e2e_process_harness.py` pattern already proven on MP1 and MP3.

## Verification status

The notebook's analysis (segmentation, cross-checks, reporting) is
verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check. The persistence/service
addition has now also been verified against a real run — see above.

## Limitations

- No fairness/bias audit performed in this pass.
- The service's single-record `/score` request assumes the caller
  already knows whether the applicant has real payment history
  (`N_PAID_INSTALMENTS > 0`) — the service itself does not decide that.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run `notebooks/04_prepayment_early_repayment_segmentation.ipynb`
   end-to-end (no dependency on Notebooks 01-03) — this also produces the
   `.joblib` bundle.
4. To run the service locally: set `API_KEY` (see `docker/.env.example`),
   then `docker compose -f 05_mega_project_5_liquidity_cashflow/docker/docker-compose.yml up --build`
   from the suite root.
