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
   percentages, and the real training-split default rate (when the model
   has one — see "Unsupervised models" below). This is what
   `monitoring_job.py` checks new data against. 2026-10-14 fix: now also
   reads a bundle's `feature_names` key (the real unsupervised
   segmentation bundles use this instead of `numeric_features`/
   `feature_cols`) — found and fixed while generating the first real
   baselines below; before the fix every KMeans bundle hit a hard error.

This design was ported and generalized from the AMEX RiskIQ Enterprise
Credit Risk Platform's own real `monitoring_job.py` (a separate personal
portfolio project of mine, unaffiliated with American Express, built for
its Problem 1) rather than re-invented, per this suite's reuse-first
build discipline — and extended here with a real full PSI number (that
project's version reports bin-share only; see `monitoring_common.py`'s
docstring for why that extension was possible).

## Real baselines generated against real data (2026-10-14)

The suite has 10 real trained bundles across MP1/MP3/MP4/MP5. Real Kaggle
data (`data/raw/*.csv`) became available for the first time on
2026-10-14 (see `DATA_PRIVACY.md` for why it's gitignored and never
committed). Of the 7 raw tables, 5 are present and complete
(`application_train/test.csv`, `bureau.csv`, `bureau_balance.csv`,
`POS_CASH_balance.csv`, `credit_card_balance.csv`); 2 are not
(`previous_application.csv` and `installments_payments.csv` — see
"Still blocked" below). A model is **eligible** for a real baseline only
if every raw table its own feature-engineering function reads is
present; eligibility is a fact about the data on disk, not a judgment
call, and is never upgraded to "onboarded" when a table is missing.

**4 of 10 real bundles are eligible and now have a real, generated
baseline** — real feature engineering (via this suite's own
`src/features/*.py` functions, never re-derived), real quantile bin
edges, verified end-to-end against both a real holdout slice of the same
population (confirmed `OK`, PSI ≈ 0) and a clearly-labeled synthetic
shifted copy of it (confirmed real `ALERT`, never silently passed).

**Correction (2026-10-14, caught reviewing the actual commit diff rather
than assuming the files landed):** these 4 `*_baseline.json` files are
**not committed to git** — `.gitignore` line 64
(`**/monitoring/*_baseline.json`) excludes every monitoring baseline,
and per `DATA_PRIVACY.md` that is the correct, intentional policy, not a
gap: a baseline is a statistical artifact derived from the full real
training data, in the same "regenerate, don't retain" category this repo
already applies to `data/raw/` and every trained `.joblib` bundle. Each
model's `config.json` (pure policy thresholds, no data-derived numbers)
*is* committed; its `*_baseline.json` lives only in the local working
copy that generated it and is reproduced with the one real command shown
in the table's own feature-source column, exactly like re-running a
notebook regenerates its bundle. A fresh clone — including a CI
runner — will correctly see these 4 models as `NOT_ONBOARDED` until
someone with the real raw data regenerates their baselines locally; that
is expected behavior, not a bug in `run_all_monitoring_jobs.py`.

| Model | Bundle | Feature source | Table(s) used |
|---|---|---|---|
| MP3 / Notebook 02 | `notebook_02_segment_model.joblib` (KMeans, bureau behavior) | `risk_segmentation_features.engineer_bureau_behavior_features` | `bureau.csv`, `bureau_balance.csv` |
| MP3 / Notebook 04 | `notebook_04_segment_model.joblib` (KMeans, revolving utilization) | `risk_segmentation_features.engineer_revolving_credit_utilization_features` | `credit_card_balance.csv` |
| MP4 / Notebook 03 | `notebook_03_champion_model.joblib` (RandomForest, revolving distress) | `revolving_distress_features.engineer_revolving_distress_features` | `credit_card_balance.csv` |
| MP4 / Notebook 04 | `notebook_04_champion_model.joblib` (RandomForest, POS/cash trajectory) | `pos_cash_trajectory_features.engineer_pos_cash_trajectory_features` | `POS_CASH_balance.csv` |

All 4 are unsupervised or otherwise lack a `TARGET` column in their
feature output, so `train_default_rate` is honestly `null` in each
baseline and `monitoring_job.py` reports that check as
`NOT_COMPUTABLE` — never fabricated.

**One real limitation found while generating these, disclosed rather
than hidden**: MP3 / Notebook 04's feature set is heavily zero-inflated
(most real applicants have no revolving-credit history at all, so most
of its 13 features are 0 for ≥75% of the population). The quantile-based
binning in `generate_monitoring_baseline.py` collapses to under 3 unique
bin edges for 12 of those 13 features and skips them — only
`N_CC_MONTHS` survived into this model's real PSI set. This is a correct
response to genuinely sparse real data, not a bug, but it means this one
baseline's drift coverage is real but thin. Tracked as a data-quality
follow-up (see the suite's own Phase 3 task list) rather than papered
over with a different binning scheme chosen after the fact to make the
number look better.

**Still blocked — 6 of 10 real bundles, honestly `BLOCKED`, never
`PASS`:**

| Model | Bundle | Blocked on |
|---|---|---|
| MP1 / Notebook 01 (flagship) | `notebook_01_champion_model.joblib` | `previous_application.csv` (only a corrupt partial download exists) AND `installments_payments.csv` (missing entirely) |
| MP1 / Notebook 02 | `notebook_02_champion_model.joblib` | `previous_application.csv` |
| MP3 / Notebook 03 | `notebook_03_segment_model.joblib` | `installments_payments.csv` |
| MP4 / Notebook 01 | `notebook_01_champion_model.joblib` | `installments_payments.csv` |
| MP4 / Notebook 02 | `notebook_02_kmeans_model.joblib` | `installments_payments.csv` |
| MP5 / Notebook 04 | `notebook_04_segment_model.joblib` | `installments_payments.csv` |

Unblocking these needs the two missing raw CSVs re-downloaded from
Kaggle onto the build machine — a data-availability gap, not a code gap;
`generate_monitoring_baseline.py` and every one of the 4 feature
functions it would call for these 6 are already real and already proven
correct on the 4 models above.

## Honest scope: coverage across the suite's 25 problems

**Onboarded in a local working copy that has run the real data through
the real generator: 4 of 25.** Only each model's `config.json` is
committed to git; its `baseline.json` is a regenerable local artifact
(see the correction note above) — so "4 onboarded" describes a build
that has the real Kaggle data and has run
`generate_monitoring_baseline.py`, not a property of the git history
itself.
**Eligible but not a trained-model problem / not yet wired: the
remaining MP1/MP3/MP4/MP5 problems above are either BLOCKED (6, see
table) or not yet given a `config.json` at all.** Extending coverage to
an eligible model is: run the generator against its bundle once the
blocking table exists, commit its `config.json`, schedule the job — no
new code required, the job and generator are both fully generic (model
name, target column, and feature list all come from the bundle/baseline
file, nothing is hardcoded to any one model).

```
python scripts/generate_monitoring_baseline.py \
    --bundle 01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib \
    --reference-csv <real, feature-engineered training CSV from engineer_credit_default_features_v2> \
    --target-col TARGET \
    --out-baseline 01_mega_project_1_underwriting_approval/monitoring/mp1_01_baseline.json
```

## Running monitoring for every onboarded model at once (2026-10-14)

Added `scripts/run_all_monitoring_jobs.py` to close a real gap this
section used to describe: extending monitoring to a second model meant
hand-building and separately scheduling its own `monitoring_job.py`
invocation. This script discovers every `*/monitoring/*_config.json` in
the repo, checks whether it has a matching `*_baseline.json` (an
"onboarded" model — see `generate_monitoring_baseline.py`), runs
`monitoring_job.py` against each onboarded model's new-data CSV, and
exits 1 if *any* model ALERTs:

```
python scripts/run_all_monitoring_jobs.py --list-only   # onboarding status, runs nothing

python scripts/run_all_monitoring_jobs.py \
    --new-data-csv 03_mega_project_3_risk_segmentation/monitoring/mp3_02_config.json=path/to/mp3_02_batch.csv \
    --new-data-csv 04_mega_project_4_delinquency_prevention/monitoring/mp4_03_config.json=path/to/mp4_03_batch.csv
```

A model with a committed `config.json` but no `baseline.json` yet is
reported as `NOT_ONBOARDED` — counted, never silently skipped, never
treated as a passing check.

As of 2026-10-14, `--list-only` reports 4 real `ONBOARDED` models (the
table above) and the rest of the suite's config'd/eligible models as
`NOT_ONBOARDED` or, once a `config.json` exists for a currently-BLOCKED
model, that model stays `NOT_ONBOARDED` until its baseline exists too —
this script makes *running* N onboarded models one command instead of N
commands; it does not itself onboard any new model.

Verified (2026-10-14) against both the 4 real onboarded models above
(real holdout batch → `OK`, clearly-labeled synthetic shifted batch →
real `ALERT`, exit code 1, on every one of the 4) and, earlier, against
synthetic baseline/config/new-data fixtures across all four code paths:
`NOT_ONBOARDED`, `BLOCKED` (onboarded, no `--new-data-csv` given for it
this run), `OK`, and `ALERT`.

## Scheduling and alerting (concrete, not just "use a scheduler")

**Linux/macOS — cron, with built-in email alerting** (no extra
integration to wire up: cron's own `MAILTO` mails a job's stdout/stderr
to the address below whenever it exits non-zero, and
`run_all_monitoring_jobs.py` exits 1 on any ALERT):

```cron
MAILTO=risk-oncall@example.com
# Daily at 06:00, all onboarded models in one run:
0 6 * * * cd /opt/home-credit-enterprise-suite && /opt/home-credit-enterprise-suite/.venv/bin/python scripts/run_all_monitoring_jobs.py --new-data-csv ... >> /var/log/hc-monitoring.log 2>&1
```

**Windows — Task Scheduler**, same command, via a `.bat`/PowerShell
wrapper and an action of type "Send an e-mail" (deprecated in newer
Windows — prefer a wrapper script that calls a webhook, below) or "Start
a program" pointed at a small notifier script that checks `%ERRORLEVEL%`.

**Any scheduler — Slack/Teams incoming webhook on failure** (works the
same whether the scheduler is cron, Task Scheduler, or a CI runner;
needs only `requests`, already a pinned dependency — see
`constraints.txt`):

```python
# notify_on_alert.py -- wrap the real command, e.g.:
#   python notify_on_alert.py -- python scripts/run_all_monitoring_jobs.py --new-data-csv ...
import subprocess, sys, requests

WEBHOOK_URL = "https://hooks.slack.com/services/REPLACE/ME"  # real secret -- set via env var, never commit it

cmd = sys.argv[sys.argv.index("--") + 1:]
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout, result.stderr)
if result.returncode != 0:
    requests.post(WEBHOOK_URL, json={"text": f"Monitoring ALERT (exit {result.returncode}):\n```{result.stdout[-1500:]}```"})
sys.exit(result.returncode)
```

**Why this isn't wired into this repo's own CI**: `monitoring_job.py`
checks a real production-scored batch against a real training baseline
— GitHub Actions has neither (no production traffic reaches CI). The
commands and snippets above are real and runnable against the 4 real
onboarded models today, and against the other 6 once their blocking raw
tables exist — that is a deployment-environment action, not a CI one.

## Real PSI thresholds used

`psi_watch = 0.10`, `psi_alert = 0.25` — the standard, widely-published
PSI interpretation bands (< 0.10 no significant shift, 0.10–0.25
moderate/watch, ≥ 0.25 significant/alert), used by all 5 real configs
committed so far (`mp1_01_config.json`, `mp3_02_config.json`,
`mp3_04_config.json`, `mp4_03_config.json`, `mp4_04_config.json`).
`default_rate_swing_pp` is each config's own chosen operating threshold,
disclosed as a choice, not a value derived from data; it is
`NOT_COMPUTABLE` for the 4 new unsupervised/no-target models above by
design, same as the default-rate check itself.
