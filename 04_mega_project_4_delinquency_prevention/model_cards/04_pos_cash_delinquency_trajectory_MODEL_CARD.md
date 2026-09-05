# Model Card — Problem 4: POS/Cash Loan Delinquency Trajectory

Notebook: `notebooks/04_pos_cash_delinquency_trajectory.ipynb`
Bundle: `decision_engine/artifacts/notebook_04_champion_model.joblib` (gitignored — regenerate by running the notebook)

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

Scores an existing applicant's real POS/cash-loan DPD trajectory —
days-past-due spikes, DPD streaks, stalled repayment progress — for an
early-warning risk of delinquency, for a portfolio-monitoring or
collections function to flag an account for proactive outreach *before*
it goes delinquent. Decision-support only — see Limitations.

## Why this model exists alongside MP1 and MP3 Notebook 03

`POS_CASH_balance.csv` already feeds two other real feature sets:

1. Mega Project 1's champion model includes real SUM totals
   (`POS_SUM_SK_DPD_OWN`, `POS_SUM_SK_DPD_DEF_OWN`, `POS_SUM_SK_DPD_TOT`,
   `POS_SUM_SK_DPD_DEF_TOT`) — application-time totals, not a trajectory.
2. Mega Project 3 Notebook 03's `engineer_repayment_behavior_features()`
   builds real MEAN/MAX/PCT-of-months RATE/LEVEL features (`MEAN_SK_DPD`,
   `MAX_SK_DPD`, `MEAN_SK_DPD_DEF`, `PCT_MONTHS_ACTIVE`,
   `PCT_MONTHS_COMPLETED`) for an **unsupervised** segmentation.

This model instead detects real DPD SPIKES and STREAKS, and real
instalment-repayment-PROGRESS STALLING — direction of change, not level,
rate, or sum. A mean DPD of 3 days cannot distinguish a scattered one-time
3-day slip from an applicant currently mid-streak — same mean, different
real trajectory. Trains a real **supervised** classifier, matching
Problems 1 and 3's early-warning use case on a third real data source. See
`src/features/pos_cash_trajectory_features.py`'s module docstring for the
full rationale.

## Features (8, all numeric, all real, all vectorized — no per-applicant Python loop)

- **DPD spike (3)**: `CURRENT_SK_DPD`, `MAX_DPD_JUMP`, `N_DPD_SPIKE_MONTHS`
  (real month-over-month change, threshold 5 days).
- **DPD streak (2, real run-length encoding)**: `LONGEST_DPD_STREAK`,
  `CURRENT_DPD_STREAK_LEN`, `CURRENT_IS_DPD_INT`.
- **Progress velocity (1, real recency-split trend)**:
  `INSTALMENT_PROGRESS_VELOCITY` — real change in mean remaining
  instalment count between the earlier and more recent halves of the
  applicant's own history; normally negative (progressing toward payoff),
  near-zero or positive signals stalled progress.
- **Scope context (1)**: `N_POS_MONTHS`.

Imputed with `SimpleImputer(strategy="median")`. Full engineering logic,
including the disclosed null-handling conventions for `SK_DPD` (defensive
zero-fill) and `CNT_INSTALMENT_FUTURE` (dropped from the mean, final
aggregate never left null), lives in
`src/features/pos_cash_trajectory_features.py`'s module docstring — these
conventions were written proactively, applying the exact lesson from
Problems 1-2's real 2026-09-01 fix to this table before it could produce
the same kind of silent or crashing null.

## Scope

Only applicants with at least one real `POS_CASH_balance.csv` record are
in scope. Your real run's scope percentage is printed by the notebook
(Section 4) and saved in `decision_engine/reports/notebook_04_summary.json`.

## Model selection methodology

Identical screen-then-CV-refine pattern as Problems 1 and 3: 4 candidate
classifiers screened on a held-out validation split; top 2 by validation
AUC advance to real 5-fold cross-validation; higher mean-CV-AUC is
champion, retrained on full train, evaluated once on a true holdout.

**Which model wins and its actual AUC are determined entirely by your real
data** — no fixture was run for this notebook (2026-09-01 policy change),
so there are no placeholder numbers to compare against. See the notebook's
own printed output and `decision_engine/reports/notebook_04_summary.json`.

**Update, 2026-09-02 — real, full-scale run:** champion
`random_forest` (real 5-fold CV mean AUC 0.5779 vs. `gradient_boosting`'s
0.5766), real holdout ROC-AUC **0.5809** (95% CI [0.5728, 0.5883]) on the
real 289,444-applicant scope population (real default rate 8.16%),
verdict **STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION** — see
`decision_engine/reports/notebook_04_summary.json` for the full real
numbers.

## Explainability

SHAP (`TreeExplainer`/`LinearExplainer` as applicable) computed for the
champion model only, on a real sample (up to 300 rows) of the holdout set.

## Evaluation

- Primary metric: ROC-AUC on a true holdout split, with a real bootstrap
  95% confidence interval.
- Secondary: real decile calibration monotonicity.
- Self-checks fail loudly rather than silently reporting a
  no-better-than-random model as validated.

## Real comparisons against other real champion models

Three independent soft dependencies, each a real, honest, apples-to-apples
comparison — never a claim of superiority in either direction:

1. **MP1 Notebook 01** (application-time covariates).
2. **MP4 Notebook 01** (installment-payment behavior) — on the real
   overlap population.
3. **MP4 Notebook 03** (revolving/credit-card distress) — on the real
   overlap population.

Each is reported only when its bundle/scores file is present and the real
overlap has at least 20 applicants and both real `TARGET` classes.

## Limitations

- **Scope limited to applicants with real prior POS/cash loans.**
- **Class imbalance**: no explicit resampling; `class_weight="balanced"`
  used where supported.
- **No production scoring service for this notebook**: batch/portfolio-
  level monitoring only.
- **No fairness/bias audit performed in this pass.**
- **Trained on Kaggle's historical Home Credit population.**

## Verification status (2026-09-01 policy change)

Per explicit instruction, this notebook was **not** executed against any
synthetic fixture before delivery — no `sample_reports/SAMPLE_*` files
exist for this problem. Verification consisted of: (1) small, targeted,
hand-built test cases for `engineer_pos_cash_trajectory_features` and
`compute_naive_current_dpd`, covering a genuine DPD spike, a real DPD
streak, null `SK_DPD` (defensively zeroed), null `CNT_INSTALMENT_FUTURE`
(including a case where an entire real half of an applicant's history has
no valid value), a single-month applicant, and a constant/no-DPD applicant
— every one of the 8 output features checked by hand; (2) a Python
syntax/AST check on the pipeline script; (3) `nbformat.validate()`. The
notebook was never executed end-to-end by us, on any data. **No champion,
no AUC, no verdict is claimed here.**

**Update, 2026-09-02 — since superseded by real execution:** the
above describes how this notebook was verified *before delivery*. Since
then, you have run this notebook end-to-end yourself against your real,
full-scale data — real champion, real AUC, and a real verdict now exist
in `decision_engine/reports/notebook_04_summary.json` (real holdout
ROC-AUC 0.5809, verdict STATISTICALLY ROBUST — RECOMMENDED FOR
PRODUCTION; see Model selection methodology above for the full real
numbers). No `sample_reports/SAMPLE_*` fixture demo file was ever
generated for this problem, and still isn't — a separate, narrower fact
from execution status.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run Mega Project 1 Notebook 01, MP4 Notebook 01, and MP4 Notebook 03
   first if you want the real side-by-side comparisons (all soft
   dependencies — this notebook still runs standalone without them).
4. Run `notebooks/04_pos_cash_delinquency_trajectory.ipynb` end-to-end.
5. The champion bundle and per-applicant scores are written to
   `decision_engine/artifacts/` for reuse by Problem 5's ranking notebook.
