# Model Card — Problem 4: Revolving Credit Utilization Segmentation

Notebook: `notebooks/04_revolving_credit_utilization_segmentation.ipynb`
Hard dependency: `decision_engine/artifacts/notebook_01_risk_tiers.csv` (this
Mega Project's own Notebook 01 — `SK_ID_CURR`, `PD`, `TARGET`, `RISK_TIER`)
Soft dependencies (cross-check only): `decision_engine/artifacts/notebook_02_bureau_segments.csv`
(Notebook 02 — `BUREAU_SEGMENT`) and `decision_engine/artifacts/notebook_03_repayment_segments.csv`
(Notebook 03 — `REPAYMENT_SEGMENT`)
Shared module: `src/features/risk_segmentation_features.py` —
`engineer_revolving_credit_utilization_features()`

## This trains no supervised model and scores no PD

PD is reused unchanged from Mega Project 3 / Notebook 01 — never
re-scored here. This notebook applies real unsupervised K-Means clustering
to a real revolving-credit-utilization feature set, grouping applicants by
credit-card usage-pattern similarity, never trained against real `TARGET`.

## Why this is a genuine, not redundant, fourth axis

Problem 1 tiers applicants by real PD LEVEL. Problem 2 clusters applicants
by real EXTERNAL bureau behavior — credit history at OTHER institutions.
Problem 3 clusters applicants by real INSTALMENT-LOAN repayment conduct
(`installments_payments.csv` / `POS_CASH_balance.csv`). This notebook
touches none of those tables. Its real 13-feature set is built entirely
from real `credit_card_balance.csv` — the applicant's own actual
month-by-month credit-card balance, credit limit, drawings, and
minimum-payment record on PREVIOUS Home Credit REVOLVING loans — see
`src/features/risk_segmentation_features.py`'s own disclosure for the full
feature list. Section 9 of the notebook computes real Cramer's V between
this notebook's segments and Problem 1's Risk Tier and (when available)
Problem 2's Bureau Segment AND Problem 3's Repayment Segment — the most
cross-axis independence evidence gathered for any MP3 problem so far, as
honest, computed evidence, not an asserted claim.

## Fixture extension: real cash-advance columns added (v1.6.8)

`fixture/credit_card_balance.csv` was originally created (for Notebook 02's
multi-table integration verification) with only the 11 real Kaggle columns
Mega Project 1's champion model and Mega Project 2's capital notebooks
needed at the time — it did not include the real `AMT_DRAWINGS_ATM_CURRENT`
/ `CNT_DRAWINGS_ATM_CURRENT` columns this notebook's real cash-advance
feature needs. `extend_fixture_credit_card_balance.py` appended those two
real Kaggle columns in place, keyed off the existing real
`AMT_DRAWINGS_CURRENT` column for internal consistency (real cash advances
are a real subset of total real drawings, never larger) — every existing
row and every existing column's values are preserved byte-for-byte, so
Mega Project 1 and 2's already-verified fixture results are unaffected.
The user's real `credit_card_balance.csv` already has the full real Kaggle
schema, so this only affects fixture verification, never the real run.

## Real fixture result

Data-driven K selection (`sklearn.metrics.silhouette_score` across
candidates k=2..8, real per-candidate minimum-cluster-size rejection at 1%
of the clustered population — both defaults applied pre-emptively per
Notebook 03's real-data lesson, not discovered the hard way here) chose
**k=7** on the fixture (highest real silhouette score, 0.184, among all 7
candidates tried — every candidate cleared the 1% floor on this small
fixture). 1,034 of 4,000 real fixture applicants (25.9%) have real
previous-loan revolving-credit history and were clustered (segment sizes
130/179/343/32/37/86/227); the remaining 2,966 (74.1%) were reported as
their own explicit "No Revolving Credit History" segment, never imputed.
Real default rate across the 8 total segments spans 12.5% to 18.5%. Real
cross-checks: Cramer's V=0.051 against Problem 1's Risk Tier, 0.043 against
Problem 2's Bureau Segment, and 0.130 against Problem 3's Repayment
Segment — all evidencing this is a real, independent fourth axis, though
the Repayment Segment cross-check is the least independent of the three
(still a moderate-low association, not a relabeling).

**Statistical Robustness Verdict on the fixture: NOT YET STATISTICALLY
ROBUST** — the chi-square test against real `TARGET` did not reach
significance at this scale (p=0.949, Cramer's V=0.023, 95% bootstrap CI
[0.023, 0.070], entirely below this suite's 0.05 materiality threshold).
This is the same expected fixture-scale limitation already documented for
Problems 2 and 3 (`LESSONS_LEARNED.md` #3) — real, honestly computed, not
a code defect. All structural Pipeline Integrity Checks pass; the notebook
completes and reports fully regardless of the statistical verdict.

## Advanced error tackling applied

- **Hard dependency** on this Mega Project's own Notebook 01 output,
  checked by actual required columns present, not just file existence
  (`LESSONS_LEARNED.md` #4) — PD is reused unchanged, never re-scored.
- **Two soft dependencies** on Notebook 02's real Bureau Segment output and
  Notebook 03's real Repayment Segment output — each used only for an
  additional cross-axis independence check in Section 9; this notebook
  still produces a complete, standalone result if either or both are
  absent (disclosed explicitly in the notebook's own printed output).
- **No `monotonic_within_noise()` call in this notebook, by design**:
  revolving-usage clusters are unordered categorical segments with no
  expected direction — the same reasoning already established three times
  in this suite (MP2 Notebook 05's HHI analysis, MP3 Notebooks 02 and 03).
- **No `matplotlib.use(...)` call anywhere in this file**
  (`LESSONS_LEARNED.md` #7).
- **Real, disclosed sampling for computational tractability**: silhouette
  score uses scikit-learn's own `sample_size` parameter.
- **Data-driven K, never fixed by hand**: the achieved cluster count is
  whatever the real silhouette score across the candidate range supports.
- **Applicants with zero real previous-loan revolving-credit history are
  never silently imputed** into a cluster with fabricated average values —
  reported as their own explicit "No Revolving Credit History" segment.
- **Real, disclosed null handling**: a real month with no minimum payment
  due has a null `AMT_INST_MIN_REGULARITY` — dropped from the
  minimum-payment-ratio and minimum-payment-only aggregations (never
  treated as 0, which would fabricate an "underpaid" signal), but every
  real month is still counted in `N_CC_MONTHS`.
- **Real, disclosed winsorization applied FROM THE START, not discovered
  the hard way**: the 9 unbounded real features are clipped to the real
  1st/99th percentile of the with-history population before
  `StandardScaler` — pre-emptively applying Notebook 03's real-data lesson
  (unclipped unbounded features let a handful of extreme real values
  dominate Euclidean distance and cause K-Means to isolate them as their
  own tiny outlier cluster) rather than discovering it live on this
  notebook's own real run. The exact per-feature bounds and clip counts
  are printed in full and saved in the JSON summary and Excel workbook,
  never silently applied.
- **K range starts at 2 and the stability floor defaults to 1% (not 3%)**
  — also a pre-emptive application of Notebook 03's real-data diagnosis
  (a real population may only support a small number of broad, stable
  segments, and the true minimum-viable real minority-group size can be
  closer to 1% than 3%). Both remain config-overridable in
  `project_config.json` (`revolving_segment_k_min`,
  `revolving_segment_k_max`, `revolving_segment_min_cluster_fraction`) if
  this notebook's own real run needs different values.

## Statistical Robustness Verdict vs. Pipeline Integrity Checks

Same two-tier pattern as every classifier-adjacent notebook in this suite:
chi-square significance, Cramer's V CI clearing the 0.05 materiality
threshold, a finite positive silhouette score, and every segment meeting
the minimum stable size are the **Statistical Robustness Verdict** — a
separate, stricter gate from the structural **Pipeline Integrity Checks**
reported alongside it. A segmentation can fail the former while passing
the latter (as it does here on the fixture); that is real and expected,
not a code defect.

## Limitations

- The real feature set is drawn entirely from the applicant's own
  PREVIOUS Home Credit REVOLVING loans (`credit_card_balance.csv`). It
  says nothing about instalment-loan repayment conduct (Problem 3 covers
  that) or external bureau behavior (Problem 2 covers that).
- Real Kaggle `credit_card_balance.csv` only has rows for applicants whose
  previous loans included a real revolving/credit-card product — most
  applicants (74.1% on the fixture) have none by construction, not by data
  gap; the "No Revolving Credit History" segment is the honest label for
  that real population, not a placeholder to be filled in later.
- K-Means assumes roughly spherical, similarly-sized clusters in the
  scaled feature space; `sklearn.preprocessing.StandardScaler` is applied
  first so no single raw-scale feature dominates the distance metric by
  construction, and winsorization further bounds real outlier influence
  (see above).
- The minimum-cluster-fraction floor (default 1% of the clustered
  population, applied from the start per Notebook 03's lesson) is a
  disclosed choice, not a fitted optimum.
- On this suite's small synthetic fixture, the statistical robustness
  verdict is NOT YET ROBUST (see above) — expected at this scale; this
  notebook's own machinery will report honestly whether real ~307K-scale
  data clears the same bar.

## Deployable service (hardening pass)

This notebook now persists its real, chosen K-Means model, its real fitted
`StandardScaler`, its real winsorize bounds, and its real feature list to
`decision_engine/artifacts/notebook_04_segment_model.joblib` (a small,
additive change — the clustering/winsorization logic itself is
unchanged). This is what makes
`services/utilization_segment_assignment_service.py` possible: a real
deployable FastAPI service that assigns a NEW real applicant to a segment
using the exact same fitted model and winsorize bounds, never retraining
or fabricating an assignment. Verified bit-identical against a real
applicant already present in this notebook's own output CSV (see
`tests/test_scoring_services.py`).

## Reproducibility

Deterministic given `RANDOM_SEED` (KMeans' `random_state`, the silhouette
sampler's `random_state`, and the bootstrap's `numpy.random.Generator`;
`n_init=10` in KMeans further stabilizes the result against any single
random initialization). Idempotent: re-running overwrites the same output
paths given the same upstream Notebook 01 (and, when present, Notebooks 02
and 03) output.
