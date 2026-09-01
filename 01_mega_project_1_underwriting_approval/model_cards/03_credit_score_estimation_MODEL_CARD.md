# Model Card — Problem 4: Credit Score Estimation

Notebook: `notebooks/03_credit_score_estimation.ipynb`
Service: `services/credit_score_service.py` (FastAPI, port 8003)
Bundle used (read-only, not retrained): `decision_engine/artifacts/notebook_01_champion_model.joblib`

## This is not a separately trained model

Unlike Problems 1 and 3, this notebook does **not** train a new model. It
loads Notebook 01's real champion model and applies a deterministic
scorecard transform to its predicted probability of default (PD). This
card documents that transform, not a training methodology, because there
is none to document here.

## The PDO scorecard transform

```
BASE_SCORE = 600.0
BASE_ODDS  = 50.0
PDO        = 20.0            # points to double the odds
FACTOR     = PDO / ln(2)
OFFSET     = BASE_SCORE - FACTOR * ln(BASE_ODDS)

odds       = (1 - PD) / PD
raw_score  = OFFSET + FACTOR * ln(odds)
SCORE      = clip(raw_score, 300, 900)
```

**This is an explicitly disclosed assumption, not something derived from
this data.** `BASE_SCORE=600`, `BASE_ODDS=50`, and `PDO=20` are a standard
credit-scorecard convention (FICO-style), chosen because it is a widely
recognized format for presenting a PD as a human-readable score — not
because the Home Credit data implies these specific constants. A real
production deployment should calibrate these constants (or a full
scorecard, e.g. via WOE/logistic-regression binning) against the
institution's own target odds-at-a-reference-score and score range.

## Explainability

SHAP + LIME are computed for the **upstream champion model** (Notebook
01's), since the PD driving the score comes from that model — there is no
separate model to explain here, and duplicating explainability on an
identical PD would be redundant, not additive.

## Statistical robustness verdict vs. pipeline integrity checks

This notebook has its own 4-check statistical robustness gate (holdout-AUC
CI, calibration gap, split-half PSI stability, and — specific to this
notebook — `score_monotonicity_holds`, i.e. does SCORE decrease as PD
increases, as it must by construction of the transform), separate from its
Pipeline Integrity Checks. On a small or synthetic run it is real and
expected for the calibration-gap check in particular to fail while every
integrity check passes 100% — that is an honest statistical result on this
run's data, not a code defect. See `01_credit_default_prediction_MODEL_CARD.md`
for the full explanation of this distinction and `CHANGELOG.md` entry
[1.0.1] for why the verdict wording was fixed to name the failing check(s)
explicitly.

**`score_monotonicity_holds` methodology (CHANGELOG [1.0.2])**: this check
no longer requires zero adjacent-band reversals. It runs a real,
Bonferroni-corrected two-proportion z-test per adjacent score-band pair
(`src/utils/stats_checks.py`) and only fails if a reversal is itself
statistically significant — matching the real statistical tolerance every
other check in this gate already has. A reversal that isn't
distinguishable from sampling noise no longer fails this check; a
genuinely significant one still does.

## Limitations

- Inherits every limitation of Notebook 01's model (see its model card) —
  the score is only as good as the PD it's derived from.
- The specific score number a given applicant receives is **not
  independently validated against any real external credit bureau score**
  — it is a monotonic re-expression of this project's own PD, not a claim
  of equivalence to FICO, VantageScore, or any bureau score.
- Because `SCORE` is a monotonic transform of `PD`, the scorecard adds no
  new predictive information beyond Notebook 01's model — its value is
  purely presentational/regulatory-format, not incremental accuracy.

## How to reproduce

1. Run Notebook 01 first (this notebook requires its bundle to exist).
2. Run `notebooks/03_credit_score_estimation.ipynb` end-to-end.
