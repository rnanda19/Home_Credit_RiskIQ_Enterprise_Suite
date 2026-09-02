# Model Card — Problem 1: Data-Driven Risk Tier Construction

Notebook: `notebooks/01_data_driven_risk_tier_construction.ipynb`
Hard dependency: `../../01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib`
Soft dependency (enrichment only): `../../02_mega_project_2_regulatory_capital/decision_engine/artifacts/notebook_01_capital_scores.csv`

## This trains no new default-risk model

This notebook reuses Mega Project 1 / Notebook 01's already-trained real
champion model (loaded via joblib, never retrained — the same pattern Mega
Project 2 / Notebook 01 already established) to score real PD for every
real applicant. The champion model itself is unchanged; only the
feature-set-compatibility check runs before scoring (see below).

## What is genuinely new here: the tiers themselves, not the PD

Every existing PD band elsewhere in this suite — Mega Project 1's Notebooks
03/04/05, Mega Project 2's Notebooks 01/02/04 — uses the SAME fixed,
hand-picked cut points (`risk_band_from_pd()`: PD < 0.05 / 0.10 / 0.20 /
0.35). That is a disclosed, shared labeling **convention** across the
suite, never presented as statistically optimal. This notebook builds a
genuinely different segmentation: a shallow `sklearn.tree.DecisionTreeClassifier`
fit directly on real PD (the sole feature) against real `TARGET` finds
where the real data itself splits most sharply, and those real split
thresholds — not round numbers chosen by a person — become the tier
boundaries. This is a standard, real technique in credit-risk scorecard
binning (the same idea underlying published "optimal binning" / WoE-binning
tools), applied honestly here: `max_leaf_nodes` sets an upper bound on tier
count, `min_samples_leaf` prevents tiny unstable tiers, and the **achieved**
tier count is whatever the real data actually supports — never forced to
hit the requested number by construction.

## Real fixture result (verification pass, before the real 307,511-applicant run)

The real decision tree (`max_leaf_nodes=6`, `min_samples_leaf=120` — 3% of
the 4,000-row fixture) found **5 real split thresholds, producing 6 real
data-driven tiers** with default rate spanning 1.6% (Tier 1) to 99.6%
(Tier 6) — strictly monotonic, chi-square p≈0, Cramer's V=0.887 (95%
bootstrap CI [0.870, 0.904]). The real per-applicant tier assignment was
matched against Mega Project 2 / Notebook 01's real capital output for
all 4,000 applicants (100% match rate on the fixture), showing real
capital-to-EAD rate rising from the lowest to the highest tier.

## Real production run confirmed (307,511 real applicants)

The real decision tree found the same structure at production scale: **5
real split thresholds, producing 6 real data-driven tiers** (Tier 1:
142,201 applicants, mean PD 2.56%; ... Tier 6: 9,225 applicants, mean PD
42.42%), with real default rate strictly monotonic from 1.67% (Tier 1) to
50.59% (Tier 6), Cramer's V=0.377 (95% bootstrap CI [0.373, 0.382]) —
chi-square significant (chi2=43,779.76, p<0.001). The real per-applicant
tier assignment was matched against Mega Project 2 / Notebook 01's real
capital output for all 307,511 applicants (100% match rate), showing real
capital-to-EAD rate rising from 3.76% at Tier 1 to a peak of 8.82% at Tier
5, easing slightly to 8.74% at Tier 6 — real capital tracking real risk,
formally confirmed monotonic within noise by Notebook 05's own synthesis
check.

**Real Statistical Robustness Verdict: STATISTICALLY ROBUST — RECOMMENDED
FOR PRODUCTION.** All 10 structural Pipeline Integrity Checks pass. This
is this notebook's final, confirmed result on real data — no further
pipeline changes are needed.

## Advanced error tackling applied

- **Hard dependency** on MP1 Notebook 01's real champion model, checked by
  actual feature-set compatibility (`up_numeric`/`up_categorical` compared
  against what the current `credit_default_features.py` produces right
  now), not just file existence (`LESSONS_LEARNED.md` #4).
- **Soft dependency** on MP2 Notebook 01's real capital output — if
  present, a genuine capital-by-tier enrichment is reported; if absent,
  this notebook still produces a complete, standalone tiering result and
  says so explicitly (same soft-dependency posture MP1 Notebook 04
  established for MP1 Notebook 01).
- **`monotonic_within_noise()`'s ordering contract verified explicitly**:
  tiers are built ascending by real PD (Tier 1 = lowest), so both the rate
  and count arrays are reversed to "highest-expected-rate-first" order
  immediately before every call — the exact directionality bug documented
  in `LESSONS_LEARNED.md` #2, deliberately avoided here from the first
  version rather than discovered after a false FAIL.
- **No `matplotlib.use(...)` call anywhere in this file**
  (`LESSONS_LEARNED.md` #7) — lets Jupyter's own inline backend handle
  `plt.show()` with no warning, matching every other notebook's
  already-clean pattern.
- **Runtime-validated tier boundaries**: strictly increasing bin edges, no
  duplicate real thresholds, every tier non-empty, tier count ≥ 2 — a
  coding mistake in the binning step raises immediately rather than
  silently producing a broken or collapsed segmentation.
- **Real chi-square + Cramer's V + vectorized multinomial bootstrap CI**
  (Risk Tier vs. real `TARGET`) — the same ~3,000x-faster vectorized
  bootstrap technique this suite already established, never a per-resample
  `pandas.crosstab` rebuild.

## Statistical Robustness Verdict vs. Pipeline Integrity Checks

Same two-tier pattern as every classifier-adjacent notebook in this suite:
chi-square significance, Cramer's V CI excluding the robustness threshold,
default-rate monotonicity, non-empty tiers, and strictly increasing
boundaries are the **Statistical Robustness Verdict** — a separate,
stricter gate from the structural **Pipeline Integrity Checks** reported
alongside it. A tiering can fail one while passing the other; that is real
and expected, not a code defect.

## Limitations

- The tree is fit on PD alone (a single feature) by design — this notebook
  segments by risk LEVEL, not by risk DRIVER. Problems 2-4 of this Mega
  Project build genuinely different segmentation axes (bureau behavior,
  repayment discipline, revolving utilization) from real behavioral
  features Problem 1 does not touch.
- `min_samples_leaf` trades off tier granularity against tier stability —
  a smaller fraction yields more, smaller tiers that may be less stable
  under resampling; the documented default (3% of the real population) is
  a disclosed choice, not a fitted optimum.
- The capital-by-tier enrichment (Section 11) is descriptive, not itself a
  new capital methodology — it reuses Mega Project 2 / Notebook 01's real
  numbers unchanged, regrouped by this notebook's own tiers.

## Reproducibility

Deterministic given `RANDOM_SEED` (both the decision tree's `random_state`
and the bootstrap's `numpy.random.Generator`). Idempotent: re-running
overwrites the same output paths given the same upstream MP1/MP2 outputs.
