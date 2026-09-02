# Model Card — Problem 5: Early-Warning Intervention Ranking

Notebook: `notebooks/05_early_warning_intervention_ranking.ipynb`
Outputs: `decision_engine/artifacts/notebook_05_intervention_ranking.csv` (gitignored — regenerate by running the notebook)

## Intended use

Combines Problems 1-4's own real, independently-computed early-warning
signals into a single real ranking of which currently-performing accounts
most need proactive outreach, and honestly benchmarks that composite
against the simplest possible real comparator: an applicant's own current
real days-past-due. A portfolio triage aid, not an automated action
trigger — see Limitations.

## This is not a new model trained from raw data

Unlike Problems 1, 3, and 4, this notebook trains nothing new. It is a
real, disclosed **fusion** of whichever of Problems 1-4's own already-
computed real per-applicant scores are present on disk — each is a SOFT
dependency, loaded only if that notebook has already been run, never
fabricated for a missing one. This matches how this Mega Project's README
has always scoped Problem 5: "combines Problems 1-4's real signals into a
single portfolio-level ranking... benchmarked against a naive
current-DPD-only baseline."

## How the composite is built (real, disclosed, no black box)

1. Each available real signal — Notebook 01's `EARLY_DELINQUENCY_RISK_SCORE`,
   Notebook 03's `REVOLVING_DISTRESS_RISK_SCORE`, Notebook 04's
   `POS_CASH_TRAJECTORY_RISK_SCORE` — is percentile-rank-normalized to
   [0, 1] **within its own real scope population** (`pandas.Series.rank(pct=True)`),
   so a signal covering 68% of applicants and one covering 12% are each
   ranked fairly within who they actually cover.
2. Notebook 02 is a real, disclosed special case: it outputs categorical
   `PAYMENT_PATTERN` clusters, not a continuous score. Converted here to a
   real numeric proxy by mapping each pattern to **that exact run's own
   real observed default rate** for that pattern (from
   `notebook_02_summary.json`'s `pattern_agg`) — never a fabricated or
   hardcoded mapping. If the summary is missing, or a pattern has no
   matching entry, Notebook 02 is treated as unavailable rather than
   guessed at.
3. An applicant's real `COMPOSITE_SCORE` is the mean of whichever
   normalized signals that applicant actually has.
   `COVERAGE_COUNT` (1-4) is reported per applicant — never silently
   treated as 0 for a missing signal. An applicant with 0 real signals is
   out of scope, not assigned a fabricated composite.

## The naive baseline

Each applicant's most recent real `SK_DPD` from `POS_CASH_balance.csv`
(`compute_naive_current_dpd()` in
`src/features/pos_cash_trajectory_features.py`), percentile-ranked the
same way — literally "what is their DPD right now," no engineered
features, no model. This is deliberately the simplest real comparator,
per this Mega Project's own scope statement for Problem 5.

## Real statistical comparison

On the real population where a composite score, a naive-baseline score,
and real `TARGET` are all present:

- Real top-decile default-rate comparison: does the composite ranking's
  top 10% capture a real, higher observed default rate than the naive
  baseline's top 10%?
- A real chi-square test (`scipy.stats.chi2_contingency`, the same test
  already used for Problem 2's Cramer's V check) on the 2x2 contingency of
  (composite top-decile vs. naive top-decile) x (real default vs. not) —
  reported only when the evaluation population and top-decile size are
  large enough to be meaningful (≥50 and ≥5 respectively).
- A real Spearman rank correlation between the two full rankings, for
  honest context on how (dis)similar they are.

**Verdict logic** (adapted honestly for a ranking-comparison task, not a
classifier): "COMPOSITE RANKING MATERIALLY OUTPERFORMS NAIVE BASELINE"
requires ALL of: a sufficient real evaluation population (≥50), the
composite's real top-decile rate exceeding the naive baseline's, that
difference being real and statistically significant (chi-square p<0.05),
and the composite's real lift over the overall rate exceeding 1.0. Any
failure is reported as "NOT YET DEMONSTRATED TO OUTPERFORM NAIVE
BASELINE" with the specific failed check(s) named — never smoothed over
if the naive baseline wins or ties.

## Limitations

- **Depends entirely on which of Problems 1-4 you have run** — a
  composite built from 1 of 4 signals is real but thinner than one built
  from all 4; `COVERAGE_COUNT` is reported so this is never hidden.
- **Percentile normalization, not probability calibration** — the
  composite score is a real relative rank within available signals' own
  populations, not a calibrated probability; it should not be read as
  "the" probability of delinquency.
- **Notebook 02's contribution is a per-cluster average, not a
  per-applicant probability** — coarser than the other three signals by
  construction (a real, disclosed limitation of converting an unsupervised
  cluster label into a numeric proxy).
- **No production scoring service for this notebook.**
- **No fairness/bias audit performed in this pass.**

## Verification status (2026-09-01 policy change)

Per explicit instruction, this notebook was **not** executed against any
synthetic fixture before delivery. Its fusion/ranking logic (percentile
normalization, coverage-aware composite averaging) was verified with a
small, hand-built 6-applicant test case with deliberately partial,
real-world-shaped signal coverage — every composite score and coverage
count checked by hand against the input and confirmed exact. The
top-decile/chi-square/Spearman logic uses well-established
pandas/scipy calls already in use elsewhere in this suite (`nlargest`,
`chi2_contingency`, `spearmanr`) rather than new custom logic. This file's
syntax was checked (`py_compile`/`ast.parse`, 0 errors) and this notebook
passes `nbformat.validate()`. **No ranking, no lift, no verdict is claimed
here.**

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run as many of Notebooks 01-04 as you have available first (soft
   dependencies — this notebook runs with as few as 1 of the 4 present,
   and raises a clear error if 0 are present rather than fabricating a
   ranking).
4. Run `notebooks/05_early_warning_intervention_ranking.ipynb` end-to-end.
5. The real composite ranking is written to
   `decision_engine/artifacts/notebook_05_intervention_ranking.csv`.
