# Model Card — Problem 2: Installment Payment Behavior / Missed-Payment Pattern Detection

Notebook: `notebooks/02_installment_payment_behavior_detection.ipynb`
Bundle: `decision_engine/artifacts/notebook_02_kmeans_model.joblib` (gitignored — regenerate by running the notebook)

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

Groups currently-performing applicants into real, data-driven payment
*patterns* — not a risk score — based on the shape of their installment-
payment history (are they currently in a late streak, how long was their
worst-ever streak, how volatile is their payment status). Intended as a
qualitative lens for a collections or portfolio-monitoring function to
triage accounts differently: an account currently mid-streak needs
different outreach than one with an old, resolved rough patch. It is a
segmentation, not an automated action trigger — see Limitations.

## Why this model exists alongside Notebook 01

Notebook 01 predicts real `TARGET` from installment-payment *rates* (e.g.
"35% of installments were late") via a supervised classifier. A rate
cannot distinguish an applicant late on scattered, isolated installments
from one currently mid-way through a real 6-payment late streak — same
rate, materially different real risk posture. This notebook instead
detects real *streaks* — via a genuinely different feature set and a
genuinely different, **unsupervised** mechanism that never sees real
`TARGET` during fitting. See
`src/features/delinquency_features.py`'s `engineer_payment_streak_features`
docstring for the full rationale, and "Real cross-check against Notebook
01" below for honest, computed evidence of how related the two outputs
turned out to be.

## Features (7, all real, vectorized run-length encoding)

`LONGEST_LATE_STREAK`, `LONGEST_ONTIME_STREAK`, `N_LATE_STREAKS`,
`N_TOTAL_STREAKS`, `CURRENT_STREAK_IS_LATE_INT`, `CURRENT_STREAK_LEN`,
`ALTERNATION_RATE` (fraction of installment-to-installment transitions
where late/on-time status flips — a real volatility measure, distinct from
streak length). Computed via a real, vectorized shift+cumsum boundary
detection over each applicant's own chronologically-sorted installments —
no per-applicant Python loop. `StandardScaler`-normalized before
clustering.

## Real data-quality fix (2026-09-01)

**This bug crashed this notebook on real, full-scale data (307,511
applicants).** A real minority of `installments_payments.csv` rows have no
recorded `DAYS_ENTRY_PAYMENT`/`AMT_PAYMENT` — no payment has posted against
that scheduled installment as of the data snapshot (a genuine, documented
characteristic of the real Kaggle dataset). Previously, when an applicant's
*most recent* installment happened to be one of these rows, `CURRENT_STREAK_IS_LATE_INT`
came out `null` for that applicant — one `NaN` anywhere in the clustering
matrix is enough for `KMeans.fit_predict()` to raise `ValueError: Input X
contains NaN` for the *entire* real run, which is exactly what happened.
`src/features/delinquency_features.py` now has an explicit, disclosed
convention: an installment with no recorded payment is treated as
unpaid-as-of-snapshot == late, so `IS_LATE` (and everything derived from
it, including the current-streak features) is never null. The suite's own
synthetic fixture didn't originally include any such rows, which is why
this was never caught before a real, full-scale run surfaced it — the
fixture generator has since been updated to include a real minority (~3%)
of no-payment-recorded rows, including several applicants' most-recent
installment specifically, so this path is exercised on every future
verification pass. **If you hit this crash before 2026-09-01, re-pull and
re-run this notebook** — it will no longer crash, and Problem 1's
numbers are also affected (see its own model card).

## Clustering methodology

Real K-Means, with the number of clusters (`k`) chosen by the highest real
silhouette score across a documented candidate range (default 3-7),
subject to every resulting cluster meeting a minimum stable size (default
3% of scope). This is the same "achieved, not forced" data-driven-K
discipline this suite already uses elsewhere (e.g. Mega Project 3
Notebook 02). **The winning `k` and the resulting pattern profiles are
determined by your real data when you run the notebook** — this repository
does not hardcode a specific cluster count, per this project's
zero-fabrication policy. On this suite's original small synthetic fixture
(post data-quality fix, see above), k=5 was chosen (silhouette≈0.24).
**Update, 2026-09-02 — real, full-scale run:** on the real
291,643-applicant scope population, k=4 was chosen (real silhouette
score 0.5181) — see the notebook's own printed output and
`decision_engine/reports/notebook_02_summary.json` for the real numbers.

## Statistical validation

- Real chi-square test + Cramer's V (with a real bootstrap 95% CI) between
  Payment Pattern and real `TARGET`, reported as the primary robustness
  gate.
- **No monotonicity check** — by design. Unlike Notebook 01's continuous
  risk score, these are unordered categorical clusters with no expected
  direction, the same disclosed choice this suite already makes for its
  other unsupervised segmentations.
- On this suite's original small synthetic fixture (2,715 applicants), the
  honest result was **NOT YET STATISTICALLY ROBUST** (chi-square p≈0.085,
  Cramer's V 95% CI [0.032, 0.099] included 0) — reported as-is, not
  smoothed over; a small, randomly-generated fixture is not expected to
  show strong real statistical structure. **Update, 2026-09-02 — real,
  full-scale run:** on the real 291,643-applicant scope population, the
  real result is **STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION**
  (chi-square p≈6.37e-234, Cramer's V=0.0609, 95% CI [0.0572, 0.0645],
  excludes 0) — see
  `decision_engine/reports/notebook_02_summary.json` for the real numbers.

## Real cross-check against Notebook 01

When Notebook 01's real per-applicant score CSV is present, this notebook
runs a real one-way ANOVA of that continuous score across its own
categorical patterns, reporting the F-statistic, p-value, and eta-squared
as honest evidence of how related the two independently-derived real
outputs are — never gated pass/fail, and never presented as either model
validating the other.

## Limitations

- **Unsupervised — no guarantee patterns separate real risk**: the
  clustering never sees real `TARGET`; the chi-square/Cramer's V check
  exists specifically to measure, honestly, whether the resulting patterns
  happen to carry real default-rate separation. On this suite's original
  small synthetic fixture they did not clear the significance bar; on the
  real, full-scale 2026-09-02 run they did (see Statistical validation
  above).
- **No production scoring service**: like Notebook 01, this is intended
  for batch/portfolio-level monitoring, not a per-transaction API.
- **Cluster labels are stable only for this fitted `KMeans` bundle** — a
  re-run on updated data may produce a different real `k` and different
  cluster boundaries; the saved bundle is what makes labels reproducible
  for scoring new applicants against the same fitted patterns.
- **No fairness/bias audit performed in this pass.**

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle (not
   redistributed in this repo — see `data/raw/.gitkeep` at the suite root).
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. (Optional but recommended) Run Notebook 01 first for the real
   cross-check.
4. Run `notebooks/02_installment_payment_behavior_detection.ipynb`.
5. The clustering bundle and per-applicant pattern assignments are written
   to `decision_engine/artifacts/` for reuse by later MP4 notebooks (e.g.
   Problem 5's intervention ranking).
