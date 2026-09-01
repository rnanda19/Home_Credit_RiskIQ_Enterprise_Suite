---
name: Model improvement
about: Propose a change to a trained model, feature set, or scoring logic
title: "[MODEL] "
labels: model-improvement
assignees: ""
---

**Which model / notebook?**
(e.g. Notebook 01 credit-default XGBoost champion, Notebook 03 PDO
scorecard scaling constants)

**What's the proposed change?**
New feature(s), different algorithm/hyperparameters, different
preprocessing, different scorecard assumptions, etc.

**What evidence supports this change?**
Real, measured evidence only — e.g. "holdout AUC improved from X to Y on
a controlled train/test split." Do not include figures that weren't
actually measured; if you're proposing something untested, say so and
describe how you'd validate it.

**Does this change the joblib bundle contract?**
The scoring services (`services/*.py`) depend on the bundle dict having
these exact keys: `model`, `ordinal_encoder`, `imputer`, `feature_cols`,
`numeric_features`, `categorical_features`, `champion_name`. If your
change adds/removes/renames a key, please say so explicitly — the
corresponding service(s) and `MODEL_CARD.md` need updating too.

**Any impact on the MODEL_CARD.md for this problem?**
List what needs to change (training data description, known
limitations, intended use, etc).
