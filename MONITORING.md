# Production Drift Monitoring

This document exists to close a real, previously-disclosed gap: the
enterprise production-readiness review of this suite found that PSI was
used as a validation *concept* inside notebooks, but "no dedicated
monitoring/ directory or monitoring job exists anywhere in the tracked
repo." This is that missing piece.

## What exists today

Three real, tested components, added 2026-09-08:

1. **`src/monitoring/monitoring_common.py`** — a shared bin-share helper
   (`bin_share()`) plus a real, full two-sided Population Stability Index
   calculation (`psi_from_bin_pct()`): `sum((window_pct - train_pct) *
   ln(window_pct / train_pct))` over matching quantile bins.
2. **`src/monitoring/monitoring_job.py`** — the actual scheduled job. Run
   it as a daily cron job / Windows Task Scheduler task, pointed at a
   model's baseline and a batch of newly-scored production data:

   ```
   python src/monitoring/monitoring_job.py \
       --new-data-csv path/to/new_scored_batch.csv \
       --baseline-json 01_mega_project_1_underwriting_approval/monitoring/mp1_01_baseline.json \
       --config-json   01_mega_project_1_underwriting_approval/monitoring/mp1_01_config.json \
       --out-log       01_mega_project_1_underwriting_approval/monitoring/mp1_01_job_log.csv
   ```

   It checks two things: how far the new batch's realized default rate
   has swung from the training baseline (only computable once outcomes
   are known — reported as `NOT_COMPUTABLE`, not a crash, when the batch
   has no target column yet), and the real PSI of the model's top-N
   features against their training-time distribution. It appends one row
   per run to `--out-log` and exits 1 if any check is `ALERT`, so a
   scheduler can act on the exit code (fail the job, page someone).

3. **`scripts/generate_monitoring_baseline.py`** — computes a model's
   `monitoring_baseline.json` from its real trained bundle plus real
   reference data: real quantile bin edges, real per-bin training
   percentages, and the real training-split default rate. This is what
   `monitoring_job.py` checks new data against.

This design was ported and generalized from the AMEX RiskIQ Enterprise
Credit Risk Platform's own real `monitoring_job.py` (built for its
Problem 1) rather than re-invented, per this suite's reuse-first build
discipline — and extended here with a real full PSI number (AMEX's
version reports bin-share only; see `monitoring_common.py`'s docstring
for why that extension was possible).

## Honest scope: what this covers today, and what it doesn't yet

**Wired for one flagship model**: Mega Project 1, Problem 1 (Credit
Default Prediction) — the suite's most heavily reused model (see
`MODEL_REGISTRY.md`'s cross-Mega-Project consumer list). `docker/`
config template: `01_mega_project_1_underwriting_approval/monitoring/mp1_01_config.json`
(committed — pure policy thresholds, no data-derived numbers).

**Not yet generated: a real `mp1_01_baseline.json`.** This build
environment has no real, locally-downloaded Kaggle dataset (see
`DATA_PRIVACY.md` and `.gitignore`'s `data/raw/` exclusion), so
`generate_monitoring_baseline.py` cannot be run against real Home Credit
data here. It is verified structurally instead, against a small, clearly
synthetic bundle and reference CSV, in
`src/tests/test_generate_monitoring_baseline.py` — proving the script's
logic is correct, not that it has produced a real baseline yet. Whoever
next re-runs `notebooks/01_credit_default_prediction.ipynb` against the
real dataset can generate the real baseline in one command:

```
python scripts/generate_monitoring_baseline.py \
    --bundle 01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib \
    --reference-csv <your real, feature-engineered training CSV> \
    --target-col TARGET \
    --out-baseline 01_mega_project_1_underwriting_approval/monitoring/mp1_01_baseline.json
```

**Not yet extended to the other 24 problems.** Same honest shape as the
AMEX platform's own monitoring gap ("built for Problem 1 only ... the
other 13 deployable services ship with no ongoing production check") —
here it's 1 of 25. The job and generator are both fully generic (model
name, target column, and feature list all come from the bundle/baseline
file, nothing is hardcoded to Problem 1), so extending coverage to
another model is: run the generator against that model's bundle, commit
its `config.json`, schedule the job. No new code required.

**No live scheduler wired up.** This repo does not run a cron job or
Task Scheduler task itself — that's a deployment-environment concern, not
something a portfolio repo's CI can demonstrate continuously. The command
above is what such a scheduler would run.

## Real PSI thresholds used

`psi_watch = 0.10`, `psi_alert = 0.25` — the standard, widely-published
PSI interpretation bands (< 0.10 no significant shift, 0.10–0.25
moderate/watch, ≥ 0.25 significant/alert). `default_rate_swing_pp = 3.0`
is this repo's own chosen operating threshold, disclosed as a choice, not
a value derived from data — see `mp1_01_config.json`'s own comment.
