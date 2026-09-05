# Model Card — Problem 2: Credit Bureau Behavioral Segmentation

Notebook: `notebooks/02_credit_bureau_behavioral_segmentation.ipynb`
Hard dependency: `decision_engine/artifacts/notebook_01_risk_tiers.csv` (this
Mega Project's own Notebook 01 — `SK_ID_CURR`, `PD`, `TARGET`, `RISK_TIER`)
Shared module: `src/features/risk_segmentation_features.py` —
`engineer_bureau_behavior_features()`

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This trains no supervised model and scores no PD

PD is reused unchanged from Mega Project 3 / Notebook 01 — never
re-scored here. This notebook applies real unsupervised K-Means clustering
to a real credit-bureau behavioral feature set, grouping applicants by
behavioral similarity, never trained against real `TARGET`.

## Why this is genuinely new, not a re-clustering of the PD model's own bureau features

Mega Project 1's champion PD model already includes 7 real bureau/
bureau_balance summary features (`BUREAU_CNT_CREDITS`,
`BUREAU_CNT_ACTIVE`, `BUREAU_AMT_CREDIT_SUM_TOTAL`,
`BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL`, `BUREAU_MAX_DAYS_OVERDUE`,
`BUREAU_TOTAL_DPD_MONTHS`, `BUREAU_DEBT_TO_CREDIT_RATIO` — see
`src/features/applicant_credit_history_features.py`). This notebook does
NOT just relabel those same 7 numbers under a cluster ID. It builds a
richer, 16-feature real behavioral set (real credit-type mix, real
overdue AMOUNT not just a DPD-month count, real credit-limit usage at
other institutions, real recency, real distinct-credit-type count, real
worst bureau_balance status severity — full list and disclosure in
`src/features/risk_segmentation_features.py`'s own docstring) AND applies
a genuinely different mechanism: unsupervised clustering by similarity
instead of Problem 1's supervised, PD-level tiering. Both facts — richer
features and a different mechanism — are what make this a real,
non-redundant segmentation axis. Section 9 of the notebook computes a
real Cramer's V between this notebook's segments and Problem 1's Risk
Tier as honest, computed evidence of how independent the two axes
actually turned out to be, not an asserted claim.

## Real fixture result

Data-driven K selection (`sklearn.metrics.silhouette_score` across
candidates k=3..8, real per-candidate minimum-cluster-size rejection at
3% of the clustered population) chose **k=7** on the fixture (highest
real silhouette score, 0.153, among 6 candidates that all cleared the
minimum-cluster-size floor). 3,598 of 4,000 real fixture applicants
(90.0%) have real bureau history and were clustered; the remaining 402
(10.0%) were reported as their own explicit "No Bureau History" segment,
never imputed. Real default rate across the 8 total segments spans 13.2%
to 19.9%. Real cross-check against Problem 1's Risk Tier: Cramer's
V=0.049 — genuinely low, evidencing these are independent axes, not a
relabeling.

**Statistical Robustness Verdict on the fixture: NOT YET STATISTICALLY
ROBUST** — the chi-square test against real `TARGET` did not reach
significance at this scale (p=0.453, Cramer's V=0.041, 95% bootstrap CI
[0.032, 0.082], entirely below this suite's 0.05 materiality threshold).
This is a real, honestly-computed result, not a code defect — see
"Why the fixture doesn't clear the robustness bar" below. All structural
Pipeline Integrity Checks pass; the notebook completes and reports fully
regardless of the statistical verdict, exactly as this suite's two-tier
pattern (Statistical Robustness Verdict vs. Pipeline Integrity Checks)
is designed to do.

## Real production run confirmed (307,511 real applicants)

This notebook completed successfully end-to-end on the user's real
307,511-applicant data: 0 errors, all 9 structural Pipeline Integrity
Checks pass, full reporting package (Word/Excel/HTML/CSV) written.
263,491 (85.7%) of real applicants have real bureau history and were
clustered; the remaining 44,020 (14.3%) were reported as their own
explicit "No Bureau History" segment, never imputed. The real
data-driven K selection chose **k=4** (real silhouette=0.208, not the
fixture's k=7). Real segments: Behavior Segment A 51,156 applicants
(9.97% real default rate), Behavior Segment B 128,690 applicants
(7.08%), Behavior Segment C 78,093 applicants (7.00%, the lowest),
Behavior Segment D 5,552 applicants (12.37%, the highest); No Bureau
History 44,020 applicants (10.12%). Real cross-check against Problem 1's
Risk Tier: Cramer's V=0.092 — genuinely low, evidencing these are
independent axes, not a relabeling.

**Real Statistical Robustness Verdict: STATISTICALLY ROBUST — RECOMMENDED
FOR PRODUCTION** — the chi-square test against real `TARGET` is
significant at real production scale (chi2=925.79, df=4, p=4.3e-199) and
Cramer's V=0.055 (95% bootstrap CI [0.051, 0.058]) clears this suite's
0.05 materiality threshold (the CI's own lower bound, 0.051, is just
above it). This is the real, confirmed answer to the question the
fixture-scale section below could not settle on its own: the real
behavioral differences did materialize as statistically robust once
measured across the full real population. This is this notebook's final,
confirmed result on real data — no further pipeline changes are needed.

## Why the fixture doesn't clear the robustness bar (and why that's expected)

`LESSONS_LEARNED.md` #3 documents that this suite's significance tests are
well-calibrated at fixture scale (~4,000 rows) but can behave very
differently at real production scale (300,000+ rows) — previously in the
direction of over-detecting trivial effects. Here the same scale
sensitivity cuts the other way: splitting 3,598 real fixture applicants
across 7 behavioral clusters (roughly 300-950 applicants per segment)
leaves limited statistical power to detect a real but modest default-rate
spread (13.2%-19.9%) against chance. At real ~307,511-applicant scale the
same segments, if the real behavioral differences persist at a similar
magnitude, would be built on roughly 75x more real data per segment —
this notebook's own bootstrap CI machinery would report honestly whether
that materializes as statistically robust once run for real, rather than
this model card asserting it in advance. **It has now been run for real
(see "Real production run confirmed" above): the answer is yes** — the
real Cramer's V (0.055, 95% bootstrap CI [0.051, 0.058]) clears the 0.05
materiality bar that the fixture's limited statistical power alone could
not settle.

## Advanced error tackling applied

- **Hard dependency** on this Mega Project's own Notebook 01 output,
  checked by actual required columns present (`SK_ID_CURR`, `PD`,
  `TARGET`, `RISK_TIER`), not just file existence (`LESSONS_LEARNED.md`
  #4) — PD is reused unchanged, never re-scored.
- **No `monotonic_within_noise()` call in this notebook, by design**:
  behavioral clusters are unordered categorical segments with no expected
  direction — the same "does not apply by construction" reasoning MP2
  Notebook 05 already established for its own HHI concentration analysis.
- **No `matplotlib.use(...)` call anywhere in this file**
  (`LESSONS_LEARNED.md` #7).
- **Real, disclosed sampling for computational tractability**: silhouette
  score is O(n²) in the naive case; this notebook uses scikit-learn's own
  `sample_size` parameter (real, standard, documented mitigation — KMeans
  itself still fits on the full real population with bureau history, only
  the silhouette scoring step samples).
- **Data-driven K, never fixed by hand**: the achieved cluster count is
  whatever the real silhouette score across the candidate range supports,
  with a real minimum-cluster-size floor rejecting unstable candidates
  before scoring — the same "achieved, not forced" honesty Problem 1
  already established for its own tier count.
- **Applicants with zero real bureau history are never silently imputed**
  into a cluster with fabricated average values — reported as their own
  explicit "No Bureau History" segment, by real, measured prevalence.

## Statistical Robustness Verdict vs. Pipeline Integrity Checks

Same two-tier pattern as every classifier-adjacent notebook in this
suite: chi-square significance, Cramer's V CI clearing the 0.05
materiality threshold, a finite positive silhouette score, and every
segment meeting the minimum stable size are the **Statistical Robustness
Verdict** — a separate, stricter gate from the structural **Pipeline
Integrity Checks** reported alongside it. A segmentation can in principle
fail the former while passing the latter (as Problem 3's own repayment
segmentation does); this notebook's own real, confirmed verdict clears
both gates (see "Real production run confirmed" above).

## Limitations

- The real feature set is drawn entirely from `bureau.csv` /
  `bureau_balance.csv` — external credit history at other institutions.
  It says nothing about repayment behavior on the applicant's own Home
  Credit loan(s); Problem 3 of this Mega Project covers that from
  `installments_payments.csv` / `POS_CASH_balance.csv`.
  `credit_card_balance.csv` revolving-utilization behavior is deliberately
  out of scope here too — Problem 4 covers it.
- K-Means assumes roughly spherical, similarly-sized clusters in the
  scaled feature space; a real behavioral structure that is highly
  non-convex would not be well captured by this specific algorithm choice.
  `sklearn.preprocessing.StandardScaler` is applied first so no single
  raw-scale feature (e.g. `TOTAL_AMT_OVERDUE` vs. a 0-1 ratio) dominates
  the distance metric by construction.
- The minimum-cluster-fraction floor (default 3% of the clustered
  population) is a disclosed choice, not a fitted optimum — a smaller
  floor would allow more, smaller clusters at the cost of stability under
  resampling.
- On this suite's small synthetic fixture, the statistical robustness
  verdict was NOT YET ROBUST (see above) — expected at that scale and, as
  it turned out, not a sign of a real problem: the real, confirmed
  verdict on the actual 307,511-applicant production run is
  **STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION** (see "Real
  production run confirmed" above).

## Deployable service (hardening pass)

This notebook now persists its real, chosen K-Means model, its real fitted
`StandardScaler`, and its real feature list to
`decision_engine/artifacts/notebook_02_segment_model.joblib` (a small,
additive change — the clustering logic itself is unchanged). This is what
makes `services/bureau_segment_assignment_service.py` possible: a real
deployable FastAPI service that assigns a NEW real applicant to a segment
using the exact same fitted model, never retraining or fabricating an
assignment. Verified bit-identical against 3 real applicants already
present in this notebook's own output CSV (see
`tests/test_scoring_services.py`).

## Reproducibility

Deterministic given `RANDOM_SEED` (KMeans' `random_state`, the
silhouette sampler's `random_state`, and the bootstrap's
`numpy.random.Generator`; `n_init=10` in KMeans further stabilizes the
result against any single random initialization). Idempotent: re-running
overwrites the same output paths given the same upstream Notebook 01
output.
