# Model Card — Problem 3: Revolving/Credit-Card Distress Early Warning

Notebook: `notebooks/03_revolving_credit_card_distress_early_warning.ipynb`
Bundle: `decision_engine/artifacts/notebook_03_champion_model.joblib` (gitignored — regenerate by running the notebook)

## Intended use

Scores an existing applicant's real revolving/credit-card trajectory —
utilization spikes, minimum-payment-only streaks, balance-growth velocity —
for an early-warning risk of delinquency, the kind of signal a
portfolio-monitoring or collections function would use to flag an account
for proactive outreach *before* it goes delinquent. It is a decision-support
signal, not an automated action trigger — see Limitations.

## Why this model exists alongside MP1 and MP3 Notebook 04

`credit_card_balance.csv` already feeds two other real feature sets in this
suite:

1. Mega Project 1's champion model includes 8 real SUM-based totals
   (`CC_N_OWN`, `CC_SUM_UTILIZATION_OWN`, `CC_SUM_BALANCE_OWN`,
   `CC_SUM_SK_DPD_OWN`, `CC_N_TOT`, `CC_SUM_UTILIZATION_TOT`,
   `CC_SUM_BALANCE_TOT`, `CC_SUM_SK_DPD_TOT`) — application-time totals, not
   a behavioral trajectory.
2. Mega Project 3 Notebook 04's `engineer_revolving_credit_utilization_features()`
   builds real MEAN/MAX/PCT-of-months RATE features (`MEAN_UTILIZATION`,
   `MAX_UTILIZATION`, `PCT_MONTHS_MIN_PAYMENT_ONLY`, etc.) for an
   **unsupervised** segmentation — a real, static distribution summary of
   usage LEVEL.

This model instead detects real SPIKES, STREAKS, and VELOCITY — direction
of change, not level or rate. A mean utilization of 70% cannot distinguish
an applicant who has been steadily at 70% for a year from one who jumped
from 20% to 70% last month — same mean, very different real trajectory,
and the second is what an early-warning model needs to catch. It also
trains a real **supervised** classifier (predicting real `TARGET`), unlike
Mega Project 3 Notebook 04's unsupervised segmentation — matching Problem
1's early-warning use case but on a different real data source. See
`src/features/revolving_distress_features.py`'s module docstring for the
full rationale.

## Features (9, all numeric, all real, all vectorized — no per-applicant Python loop)

- **Utilization spike (3)**: `CURRENT_UTILIZATION`, `MAX_UTILIZATION_JUMP`,
  `N_UTILIZATION_SPIKE_MONTHS` (real month-over-month change, threshold
  0.15, not a static mean/max).
- **Minimum-payment-only streak (3, real run-length encoding, same
  shift+cumsum technique as Problem 2's installment streaks)**:
  `LONGEST_MIN_PAYMENT_ONLY_STREAK`, `CURRENT_MIN_PAYMENT_ONLY_STREAK_LEN`,
  `CURRENT_IS_MIN_PAYMENT_ONLY_INT`.
- **Drawdown velocity (2, real recency-split trend, same technique as
  Problem 1's `LATE_RATE_TREND`)**: `BALANCE_GROWTH_VELOCITY`,
  `DRAWINGS_VELOCITY`.
- **Scope context (1)**: `N_CC_MONTHS`.

Imputed with `SimpleImputer(strategy="median")`. Full engineering logic,
including the disclosed null-handling conventions for
`AMT_DRAWINGS_CURRENT` and `AMT_INST_MIN_REGULARITY`, lives in
`src/features/revolving_distress_features.py`'s module docstring — these
conventions were written proactively, applying the exact lesson learned
from Problems 1-2's real 2026-09-01 no-payment-recorded bug on
`installments_payments.csv` to this table before it could produce the same
kind of silent or crashing null.

## Scope

Only applicants with at least one real `credit_card_balance.csv` record are
in scope — an applicant with no prior revolving/credit-card loan has no
trajectory signal to score, and is excluded, not assigned a fabricated
default. Expected to be a smaller population than Problem 1's
installment-history scope (a revolving/credit-card product is only one of
several real Home Credit loan types). Your real run's scope percentage is
printed by the notebook (Section 4) and saved in
`decision_engine/reports/notebook_03_summary.json`.

## Model selection methodology

Identical screen-then-CV-refine pattern as Problem 1 and MP1 Notebook 01: 4
candidate classifiers (`LogisticRegression`, `DecisionTreeClassifier`,
`RandomForestClassifier`, `GradientBoostingClassifier`, all
`random_state=42`) screened on a held-out validation split; top 2 by
validation AUC advance to real 5-fold cross-validation; higher mean-CV-AUC
of the two is champion, retrained on full train, evaluated once on a true
holdout split.

**Which model wins and its actual AUC are determined entirely by your real
data when you run the notebook** — this repository does not hardcode or
claim a specific champion or accuracy number, per this project's
zero-fabrication policy, and per the 2026-09-01 policy change (see
"Verification status" below), this notebook was not run against any
fixture either — there are no placeholder numbers here to compare against.
See the notebook's own printed output and
`decision_engine/reports/notebook_03_summary.json` for your real run's
numbers.

## Explainability

SHAP (`TreeExplainer` for tree-based champions, `LinearExplainer` for
`logistic_regression`) computed for the champion model only, on a real
sample (up to 300 rows) of the holdout set.

## Evaluation

- Primary metric: ROC-AUC on a true holdout split, with a real bootstrap
  95% confidence interval.
- Secondary: real decile calibration monotonicity
  (`src/utils/stats_checks.py`'s `monotonic_within_noise`).
- Self-checks fail loudly (`champion_auc_above_random`,
  `holdout_auc_ci_excludes_random`) rather than silently reporting a
  no-better-than-random model as validated.

## Real comparisons against other real champion models

Two independent soft dependencies, both real, honest, apples-to-apples
comparisons — never a claim of superiority in either direction:

1. **MP1 Notebook 01** (application-time covariates): if MP1's champion
   bundle is present, rebuilds MP1's exact feature set and scores the SAME
   holdout population with MP1's champion.
2. **MP4 Notebook 01** (installment-payment behavior): if Notebook 01's
   real per-applicant scores CSV is present, scores it against the real
   subset of applicants BOTH notebooks' scopes share (has both installment
   AND revolving/credit-card history) — reported only when that overlap has
   at least 20 real applicants and both real `TARGET` classes present.

## Limitations

- **Smaller real scope than Problem 1** — not every applicant has a prior
  revolving/credit-card loan; this notebook cannot score applicants outside
  that scope.
- **Class imbalance**: no explicit resampling; `class_weight="balanced"`
  used where supported.
- **No production scoring service for this notebook**: intended for
  batch/portfolio-level monitoring, not a per-transaction API — see the
  root README's disclosed scope boundary for population-level analyses.
- **No fairness/bias audit performed in this pass.**
- **Trained on Kaggle's historical Home Credit population** — performance
  on a materially different applicant population is unverified.

## Verification status (2026-09-01 policy change)

Per the user's explicit instruction, this notebook was **not** executed
against any synthetic fixture before delivery — no `sample_reports/SAMPLE_*`
files exist for this problem, and none are planned. Verification instead
consisted of: (1) small, targeted, hand-built test cases for the new
`engineer_revolving_distress_features` function, covering a genuine
utilization spike, null `AMT_DRAWINGS_CURRENT`, null
`AMT_INST_MIN_REGULARITY` on multiple applicants, a single-month applicant,
and a constant-utilization applicant — every computed value checked by hand
against the input; (2) a Python syntax/AST check on the full pipeline
script (0 errors); (3) `nbformat.validate()` on the assembled notebook. The
notebook was never executed end-to-end by us, on any data, real or
synthetic. **No champion, no AUC, no verdict is claimed here.** Send the
notebook's real console output or
`decision_engine/reports/notebook_03_summary.json` after you run it, and
this model card will be updated with your real numbers.

**Update, 2026-09-02 — since superseded by real execution:** the
above describes how this notebook was verified *before delivery*
(hand-built test cases, no fixture run, no champion/AUC/verdict claimed
at build time). Since then, you have run this notebook end-to-end
yourself against your real, full-scale data. The real results now exist
in `decision_engine/reports/notebook_03_summary.json`: champion
`random_forest` (real 5-fold CV mean AUC 0.6475 vs. `gradient_boosting`'s
0.6455), real holdout ROC-AUC **0.6570** (95% CI [0.6442, 0.6707]) on the
real 86,905-applicant scope population (real default rate 8.67%), verdict
**STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION**. No `sample_reports/
SAMPLE_*` fixture demo file was ever generated for this problem, and
still isn't — that is a separate, narrower fact from execution status.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle (not
   redistributed in this repo — see `data/raw/.gitkeep`).
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Mega Project 1 Notebook 01 and MP4 Notebook 01 first if you want the
   real side-by-side comparisons (both soft dependencies — this notebook
   still runs standalone without either).
4. Run `notebooks/03_revolving_credit_card_distress_early_warning.ipynb`
   end-to-end.
5. The champion bundle and per-applicant scores are written to
   `decision_engine/artifacts/` for reuse by later MP4 notebooks (e.g.
   Problem 5's intervention ranking).
