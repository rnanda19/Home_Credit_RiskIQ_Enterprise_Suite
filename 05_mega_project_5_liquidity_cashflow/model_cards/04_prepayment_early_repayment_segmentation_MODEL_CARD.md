# Model Card — Problem 4: Prepayment / Early-Repayment Behavior Segmentation

Notebook: `notebooks/04_prepayment_early_repayment_segmentation.ipynb`
Outputs: `decision_engine/reports/notebook_04_*`,
`decision_engine/artifacts/notebook_04_segment_model.joblib` (gitignored —
regenerate by running the notebook)

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

## Real `.joblib` persistence code + service — not yet verified

Notebook 04 now has real persistence code (added 2026-09-02): it saves
`{kmeans, scaler, feature_names, segment_labels, k_chosen, random_seed,
winsorize_report}` to
`decision_engine/artifacts/notebook_04_segment_model.joblib`, and a real
FastAPI service (`services/prepayment_segment_assignment_service.py`,
port 8015) wraps that bundle using the shared
`src/serving/segment_assignment_common.py` factory. **As of this model
card's writing, the notebook has not yet been re-run since this code was
added, so no bundle exists yet and the service is unverified against real
data.** Re-run this notebook to produce the bundle, then the service can
be confirmed working end-to-end.

## Verification status

The notebook's analysis (segmentation, cross-checks, reporting) is
verified end-to-end per this suite's full protocol on your own real,
full-scale run: 0 execution errors, outputs cleared, `nbformat.validate()`
passed, a Playwright network-blocked HTML dashboard check, and a
LibreOffice headless Excel recalculation check. The persistence/service
addition itself is not yet verified against a real run — see above.

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
