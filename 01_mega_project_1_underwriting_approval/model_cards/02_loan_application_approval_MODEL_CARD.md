# Model Card — Problem 2: Loan Application Approval

Notebook: `notebooks/02_loan_application_approval.ipynb`
Service: `services/loan_approval_scoring_service.py` (FastAPI, port 8002)
Bundle: `decision_engine/artifacts/notebook_02_champion_model.joblib` (gitignored — regenerate by running the notebook)

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `18ea21c`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 4 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (e.g. `517b7f4`, from the
2026-09-02 sync, when a `polars` dependency was briefly missing from the
`shared-tests` job) — that historical failure was fixed in commit `96e4321`
and does not reflect the current state of the suite.

## Intended use

Predicts an approval-relevant probability for a loan application,
independent of but cross-referenced against Notebook 01's default-risk
model. Intended as a decision-support signal for an approval workflow, not
an automated accept/reject system — see Limitations.

## Relationship to Notebook 01

This is a genuinely **independent model** with its own candidate screen,
CV, and champion selection — it is not just a relabeled copy of Notebook
01. If Notebook 01's champion bundle
(`notebook_01_champion_model.joblib`) is present, this notebook additionally
loads it and scores Notebook 01's real PD as an **extra input feature /
cross-check**, so the two models can be compared honestly on the same
population; if that bundle is absent, this notebook still runs standalone
(that interdependency is additive, not required).

## Model selection methodology

Same 4-candidate methodology as Notebook 01: `RandomForestClassifier`,
`XGBClassifier`, `CatBoostClassifier`, `LGBMClassifier`, all seeded with 42,
screened via 5-fold CV, top-2 re-evaluated, champion retrained on the full
train split and evaluated once on a true holdout split. As with Notebook
01, **the actual champion and its AUC depend on your real data run and are
not hardcoded or claimed here.**

## Explainability

SHAP + LIME computed for the champion model only, on a real holdout sample
— same standing convention as Notebook 01.

## Evaluation

Primary metric: ROC AUC on a true holdout split. A self-check fails loudly
if holdout AUC is not above 0.5.

## Statistical robustness verdict vs. pipeline integrity checks

Same distinction as Notebook 01's model card — the Deployment/Statistical
Robustness Verdict and the Pipeline Integrity Checks are two different,
independently-computed check families, not the same result shown twice.
On the real, full-scale 2026-09-02 rerun, this notebook's Statistical
Robustness Verdict is `RECOMMENDED FOR PRODUCTION` — all deployment
checks passed (see `decision_engine/artifacts/notebook_02_summary.json`'s
`statistical_validation` field); see
`01_credit_default_prediction_MODEL_CARD.md` for the full explanation and
`CHANGELOG.md` entry [1.0.1] for why the verdict wording was fixed to name
failing checks explicitly.

## Limitations

- Same class-imbalance, fairness-audit, and adverse-action-compliance
  caveats as Notebook 01's model card apply here — not repeated in full,
  see `01_credit_default_prediction_MODEL_CARD.md`.
- The "approval" framing in this notebook name reflects the Kaggle
  competition's real target semantics for this task; it should not be read
  as a claim that this model alone constitutes a full underwriting policy
  (pricing, exposure limits, and portfolio-level constraints are out of
  scope for a single per-application model).

## How to reproduce

1. Real Home Credit dataset from Kaggle (not redistributed here).
2. (Optional but recommended) run Notebook 01 first so its champion bundle
   is available for the cross-check feature.
3. Run `notebooks/02_loan_application_approval.ipynb` end-to-end.
4. Champion bundle written to
   `decision_engine/artifacts/notebook_02_champion_model.joblib`.
