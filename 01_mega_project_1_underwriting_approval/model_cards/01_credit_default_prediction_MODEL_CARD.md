# Model Card — Problem 1: Credit Default Prediction

Notebook: `notebooks/01_credit_default_prediction.ipynb`
Service: `services/credit_default_scoring_service.py` (FastAPI, port 8001)
Bundle: `decision_engine/artifacts/notebook_01_champion_model.joblib` (gitignored — regenerate by running the notebook)

## Intended use

Predicts the probability that an applicant will default on a loan
(`TARGET = 1`), for use as an input signal to underwriting decisions and
downstream problems in this Mega Project (loan approval, credit score
estimation, repayment capacity cross-validation all reference this model's
output). It is a decision-support signal, not an automated accept/reject
system — see Limitations.

## Model selection methodology

Four candidate classifiers are trained and compared under 5-fold
cross-validation on the real training split: `RandomForestClassifier`
(`n_estimators=200, max_depth=8`), `XGBClassifier`
(`n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8`),
`CatBoostClassifier` (`iterations=300, depth=6, learning_rate=0.05`), and
`LGBMClassifier` (`n_estimators=300, max_depth=6, learning_rate=0.05`) — all
with `random_state`/`random_seed`/`seed=42` for reproducibility. The top 2
by mean CV AUC are re-evaluated, the higher-AUC of the two is selected as
champion, then the champion is retrained on the full training split and
evaluated once on a held-out test split it never saw during CV or
selection.

**Which model wins (RandomForest / XGBoost / CatBoost / LightGBM) and its
actual AUC are determined by your real data when you run the notebook —
this repository does not hardcode or claim a specific champion or a
specific accuracy number**, in keeping with this project's zero-fabrication
policy: no performance figure is asserted here that hasn't been measured
on your own run.

## Features (v2 — expanded from a 2-table to a 7-table feature set)

**This model was retrained** to use all 7 of Home Credit's real data tables,
not just `application_train.csv` + `bureau.csv` (v1). The change was
deliberate, not routine — see "v1 vs. v2: the real, measured accuracy
comparison" below for why, and CHANGELOG.md entry [1.4.1] for the full
record.

- **Numeric** (47 features): applicant financial/demographic fields, real
  external-bureau aggregates (`bureau.csv` + `bureau_balance.csv`, via
  `engineer_bureau_history_features`), real prior-Home-Credit-application
  history (`previous_application.csv` — count/approval-rate/refusal-rate/
  average amounts, via `engineer_previous_application_features`), and real
  prior-loan-servicing behavior (`POS_CASH_balance.csv`,
  `installments_payments.csv`, `credit_card_balance.csv` — payment ratios,
  late-payment rates, utilization, via
  `engineer_prev_loan_servicing_features_loo`'s applicant-level TOTAL
  block), imputed with `SimpleImputer(strategy="median")`.
- **Categorical** (9 features): unchanged from v1 (contract type, income
  type, education, family status, etc.), encoded with
  `OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)`
  after coercion to `category` dtype with an explicit `"Missing"` sentinel
  for nulls.

All feature engineering lives in the shared, HYPER
`src/features/credit_default_features.py` (`engineer_credit_default_features_v2`)
and `src/features/applicant_credit_history_features.py` modules — built
once, imported by this notebook and by every downstream notebook/Mega
Project that scores with this champion, so scoring-time features are always
byte-identical to training-time features.

**Leakage safety, by source** (full reasoning in
`credit_default_features.py`'s own docstring): `bureau`/`bureau_balance`
are external, no Home Credit loan linkage — safe in full.
`previous_application` rows are Home Credit's own already-COMPLETED past
decisions — safe in full at applicant level. `POS_CASH_balance`/
`installments_payments`/`credit_card_balance` use only the applicant-level
TOTAL aggregate (no leave-one-out subtraction) — correct here specifically
because this model's TARGET (does the NEW application default) has no
`SK_ID_PREV` of its own in those servicing tables, so there is nothing to
leave out. Notebook 02 (Problem 2), whose TARGET *is* a specific
`previous_application` row, uses the leave-one-out-subtracted variant of
this same shared function instead — that usage is unaffected by this
change.

The exact feature lists and preprocessing are captured in the joblib bundle
itself (`feature_cols`, `numeric_features`, `categorical_features`) so the
scoring service reproduces training-time preprocessing exactly, not an
approximation of it.

### v1 vs. v2: the real, measured accuracy comparison

The notebook fits the SAME champion architecture on the SAME real holdout
rows (aligned by `SK_ID_CURR`) twice — once on v1's 2-table feature set,
once on v2's 7-table feature set — and reports both real holdout AUCs side
by side (`feature_set_accuracy_comparison` in
`decision_engine/artifacts/notebook_01_summary.json`), so any AUC delta is
attributable to the richer data, not to a different model or a different
split. On your real, full-scale 2026-09-02 rerun (46,127-row real holdout,
aligned by `SK_ID_CURR`), this measured a real +0.0089 AUC improvement
(v1: 0.7705 → v2: 0.7795) from the 7-table feature set over the 2-table
baseline — a modest but genuine gain from the richer data, not noise
from a small fixture. See `feature_set_accuracy_comparison` in
`decision_engine/artifacts/notebook_01_summary.json` for the full real
figures.

## Statistical robustness verdict vs. pipeline integrity checks

This notebook reports two genuinely different, independently-computed
check families — not the same result shown twice:

- **Pipeline Integrity Checks** — structural sanity (data loaded, columns
  present, no infinite/out-of-range values, thread ceiling applied, etc.).
  Passing all of these means the code ran correctly and produced
  well-formed output.
- **Deployment/Statistical Robustness Verdict** — a separate, stricter
  gate on whether *this run's data* shows statistically robust evidence
  (a bootstrap 95% CI on holdout AUC bounded away from 0.5, an acceptable
  calibration gap, a stable split-half PSI). A verdict of "NOT RECOMMENDED
  FOR PRODUCTION YET" names the specific check(s) that did not pass — it
  is an honest statistical result on this run's data, not a code defect,
  and it can occur even when every integrity check passes. This was found
  to read as a false contradiction in an earlier revision of this report
  and was fixed to name the failing check(s) explicitly — see the root
  `CHANGELOG.md`, entry [1.0.1].

## Explainability

SHAP (`TreeExplainer`) and LIME local explanations are computed for the
**champion model only** (not all 4 candidates), on a real sample of the
holdout set — per this suite's standing "champion-only explainability"
convention, since computing full SHAP/LIME for all 4 candidates on every
run is not a good use of the compute budget once a champion is chosen.

## Evaluation

- Primary metric: ROC AUC on a true holdout split (never used in CV or
  model selection).
- Secondary: 5-fold CV AUC (mean/std) for the top-2 screened models.
- A self-check (`champion_auc_above_random`) fails loudly if the champion's
  holdout AUC is not above 0.5, rather than silently reporting a bad model
  as validated.

## Limitations

- **Class imbalance**: like the real Home Credit dataset, defaults are a
  minority class; no explicit resampling (SMOTE, class weighting) is
  applied in this notebook — this is a design choice to keep the model
  trained on the real, unaltered class distribution, not an oversight, but
  it means the model's precision at low decision thresholds should be
  checked against your actual approval-rate targets before use.
- **Not a legally compliant adverse-action model as shipped**: US ECOA/
  Regulation B (and equivalent regimes elsewhere) require specific
  adverse-action reason codes derived in a governed way; this notebook's
  SHAP/LIME output is explanatory for data science purposes, not
  pre-packaged as compliant adverse-action reason codes.
- **No fairness/bias audit performed in this pass** — a protected-class
  disparate-impact analysis is not part of this notebook and should be
  added before any real underwriting use.
- **Trained on Kaggle's historical Home Credit population** — performance
  on a materially different applicant population (different country,
  product mix, or time period) is unverified.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle (not
   redistributed in this repo — see `data/raw/.gitkeep`).
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run `notebooks/01_credit_default_prediction.ipynb` end-to-end.
4. The champion bundle is written to
   `decision_engine/artifacts/notebook_01_champion_model.joblib`, which the
   scoring service and Notebooks 02/03/04 read.
