# Model Card — Problem 1: Early Delinquency Risk Scoring

Notebook: `notebooks/01_early_delinquency_risk_scoring.ipynb`
Bundle: `decision_engine/artifacts/notebook_01_champion_model.joblib` (gitignored — regenerate by running the notebook)

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

Scores an existing, currently-performing applicant's real installment-
payment history for an early-warning risk of delinquency — the kind of
signal a portfolio-monitoring or collections function would use to flag an
account for proactive outreach *before* it goes delinquent, not a
point-of-approval underwriting decision. It is a decision-support signal,
not an automated action trigger — see Limitations.

## Why this model exists alongside Mega Project 1's champion

Mega Project 1 Notebook 01's champion model predicts default using
application-time covariates (income, employment, external bureau history) —
everything knowable at the moment of approval. This model uses the
opposite information: the applicant's own real record of what they were
scheduled to pay and what they actually paid, across every installment on
every prior Home Credit loan (`installments_payments.csv`), engineered by
the new, HYPER `src/features/delinquency_features.py` module. Both models
predict the same real `TARGET`, so this notebook loads MP1's champion (a
soft dependency, never retrained) purely to report a real, honest
side-by-side ROC-AUC comparison on the identical holdout population — see
"Real comparison against Mega Project 1" below. Neither model is claimed
to replace the other; they use data available at different points in the
loan lifecycle.

## Features (12, all numeric, all behavioral)

`N_INSTALLMENTS`, `N_PREV_LOANS_SERVICED`, `PCT_INSTALLMENTS_LATE`,
`MEAN_DAYS_LATE`, `MAX_DAYS_LATE`, `STD_DAYS_LATE`,
`MEAN_DAYS_LATE_WHEN_LATE`, `PCT_INSTALLMENTS_UNDERPAID`,
`MEAN_PAYMENT_RATIO`, `MIN_PAYMENT_RATIO`, `TOTAL_SHORTFALL_AMT`,
`LATE_RATE_TREND` (real, vectorized recency split: the change in an
applicant's own late-payment rate between the earlier and more recent
halves of their installment history — positive means recently getting
worse). Imputed with `SimpleImputer(strategy="median")`. Full engineering
logic, including the leakage rationale, lives in
`src/features/delinquency_features.py`'s module docstring.

## Scope

Only applicants with at least one real serviced installment are in scope —
an applicant with none has no behavioral signal to score, and is excluded,
not assigned a fabricated default value. On this suite's original small
synthetic verification fixture, this was 2,715 of 4,000 applicants (67.9%).
**Your real, full-scale run (2026-09-02) scored 291,643 of the real
307,511-applicant population (94.84%)** — see
`decision_engine/reports/notebook_01_summary.json` (`n_scope`, `n_app_total`)
for the real figure.

## Real data-quality fix (2026-09-01)

A real minority of `installments_payments.csv` rows have no recorded
`DAYS_ENTRY_PAYMENT`/`AMT_PAYMENT` — no payment has posted against that
scheduled installment as of the data snapshot. This is a genuine,
documented characteristic of the real Kaggle dataset, not a data-quality
problem the fixture originally replicated. `src/features/delinquency_features.py`
now has an explicit, disclosed convention for it: an installment with no
recorded payment is treated as unpaid-as-of-snapshot — `IS_LATE = True`,
`IS_UNDERPAID = True`, `SHORTFALL_AMT` = the full scheduled amount (0.0
paid so far), rather than being silently dropped from every rate/mean
aggregation as it was before this fix. This changes this notebook's real
numbers (`PCT_INSTALLMENTS_LATE`, `MEAN_PAYMENT_RATIO`, `MIN_PAYMENT_RATIO`,
`TOTAL_SHORTFALL_AMT`) for affected applicants — a correction, not a
cosmetic change. **If you ran this notebook before 2026-09-01, re-pull and
re-run it** — your prior output used the old, silently-incomplete
definition. See the sibling Problem 2 model card for the crash this same
root cause produced there.

## Model selection methodology

4 candidate classifiers (`LogisticRegression`, `DecisionTreeClassifier`,
`RandomForestClassifier`, `GradientBoostingClassifier`, all
`random_state=42`) are screened on a held-out validation split; the top 2
by validation AUC advance to real 5-fold cross-validation on the training
split; the higher mean-CV-AUC of the two is selected as champion, retrained
on the full training split, and evaluated once on a true holdout split it
never saw during screening, CV, or selection — the same screen-then-CV
champion-selection pattern used throughout this suite (e.g. Mega Project 1
Notebook 01).

**Which model wins and its actual AUC are determined by your real data
when you run the notebook** — this repository does not hardcode or claim a
specific champion or accuracy number, per this project's zero-fabrication
policy. On this suite's original small synthetic fixture (post
data-quality fix, see above), `gradient_boosting` won the real 5-fold CV
(mean AUC 0.5179) but scored a holdout ROC-AUC of 0.4678 (95% bootstrap CI
[0.4102, 0.5214]) — below chance on that particular small,
randomly-generated fixture, which is why that fixture run's honest verdict
was **NOT YET STATISTICALLY ROBUST** (fails `champion_auc_above_random`
and `holdout_auc_ci_excludes_random`), reported as-is rather than smoothed
over, on a 2,715-applicant synthetic sample only.

**Update, 2026-09-02 — real, full-scale run:** `random_forest` won the
real 5-fold CV (mean AUC 0.6051, std 0.0059) over `gradient_boosting`
(mean AUC 0.6041), and scored a real holdout ROC-AUC of **0.6032** (95%
bootstrap CI [0.5952, 0.6113]) on the real 291,643-applicant scope
population — clearing both self-checks, for a real verdict of
**STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION**. See the notebook's
own printed output and
`decision_engine/reports/notebook_01_summary.json` for the full real
numbers.

## Explainability

SHAP (`TreeExplainer` for tree-based champions, `LinearExplainer` for
`logistic_regression`) is computed for the **champion model only**, on a
real sample (up to 300 rows) of the holdout set, per this suite's standing
champion-only-explainability convention.

## Evaluation

- Primary metric: ROC-AUC on a true holdout split (never used in
  screening, CV, or model selection), with a real bootstrap 95% confidence
  interval.
- Secondary: real decile calibration — does observed default rate rise
  (within statistical/practical noise tolerance, via
  `src/utils/stats_checks.py`'s `monotonic_within_noise`) as predicted risk
  decile increases. A real, standard early-warning-score sanity check
  independent of AUC.
- Self-checks fail loudly (`champion_auc_above_random`,
  `holdout_auc_ci_excludes_random`) rather than silently reporting a
  no-better-than-random model as validated.

## Real comparison against Mega Project 1

When MP1 Notebook 01's champion bundle is present, this notebook rebuilds
MP1's exact application-time feature set (via
`engineer_credit_default_features_v2`, unchanged), scores the *same*
holdout population with MP1's champion, and reports both real ROC-AUC
numbers side by side — a genuine, apples-to-apples comparison on identical
rows, not two separately-defined evaluation sets. This is expected to
favor MP1's richer, application-time feature set; the comparison exists to
show the two signals are real and complementary (different data sources,
different points in the loan lifecycle), not to declare a winner.

## Limitations

- **Historical below-chance holdout AUC on the original small synthetic
  fixture, since superseded**: on this suite's original 2,715-applicant
  synthetic fixture, holdout ROC-AUC came back 0.4678 (verdict NOT YET
  STATISTICALLY ROBUST) and MP1's application-time feature set scored
  0.9427 ROC-AUC on that same small fixture population. **Update,
  2026-09-02 — real, full-scale run:** on the real 291,643-applicant
  scope population, this model scored a real holdout ROC-AUC of 0.6032
  (95% CI [0.5952, 0.6113], verdict STATISTICALLY ROBUST — RECOMMENDED
  FOR PRODUCTION), and MP1's champion scored a real 0.8099 ROC-AUC on the
  identical real holdout population — see
  `decision_engine/reports/notebook_01_summary.json`. MP1's richer
  application-time feature set still outperforms this behavioral-only
  signal on real data, as expected; the two remain complementary, not
  competing.
- **Class imbalance**: no explicit resampling is applied; `class_weight="balanced"`
  is used where the candidate model supports it.
- **No production scoring service for this notebook**: unlike Mega
  Projects 1-3's per-record services, an early-warning behavioral score is
  intended for batch/portfolio-level monitoring, not a per-transaction API
  — see the root README's disclosed scope boundary for population-level
  analyses.
- **No fairness/bias audit performed in this pass.**
- **Trained on Kaggle's historical Home Credit population** — performance
  on a materially different applicant population is unverified.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle (not
   redistributed in this repo — see `data/raw/.gitkeep`).
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Mega Project 1 Notebook 01 first if you want the real side-by-side
   comparison (soft dependency — this notebook still runs standalone
   without it).
4. Run `notebooks/01_early_delinquency_risk_scoring.ipynb` end-to-end.
5. The champion bundle and per-applicant scores are written to
   `decision_engine/artifacts/` for reuse by later MP4 notebooks (e.g.
   Problem 5's intervention ranking).
