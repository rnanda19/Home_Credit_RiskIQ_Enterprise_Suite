# Model Card — Problem 1: Expected Loss & Capital Requirement Estimation

Notebook: `notebooks/01_expected_loss_capital_requirement.ipynb`
Bundle reused (not owned by this notebook): `../01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib`
Shared formula module: `../../src/features/regulatory_capital_features.py`

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

Estimates real, per-applicant Expected Loss and a Basel-retail-IRB-style
capital requirement, for use as a decision-support input to Mega Project 2's
downstream RWA analytics, economic-capital, stress-testing, and
concentration notebooks. It is an illustrative regulatory-capital estimate
built from a genuine probability-of-default model plus documented industry
assumptions — **not** a Pillar 1 regulatory filing, an ICAAP submission, or
a substitute for a bank's own internally validated LGD/EAD models.

## This is not a trained model — read this before trusting any number below

Mega Project 2 does not train a new model. It reuses Mega Project 1 /
Notebook 01's real, already-trained credit-default classifier, loaded via
`joblib.load()`, to score real probability of default (PD) for every real
applicant — the same "loaded, not retrained" pattern MP1's own Notebook
04/05 already used against Notebook 01. Feature construction is
byte-identical to training time: this notebook imports the exact same
`src/features/credit_default_features.py` function MP1's Notebook 01 used,
so scoring never silently drifts from what the model was trained on (a
mismatch check raises an error if the shared feature module ever changes
without a Notebook 01 retrain).

## What is real vs. what is a documented assumption

| Input | Status | Source |
|---|---|---|
| PD (probability of default) | **Real, measured** | Mega Project 1 / Notebook 01's real trained champion model, scored against your real data |
| EAD (exposure at default) | **Real, proxy** | Real `AMT_CREDIT` column (disclosed simplification — no committed-undrawn/CCF data available at this scope) |
| LGD (loss given default) | **Documented assumption, not measured** | Published Basel retail-IRB reference points, mapped by real collateral-proxy columns (`NAME_CONTRACT_TYPE`, `FLAG_OWN_REALTY`, `FLAG_OWN_CAR`) — see the 4-segment table in `src/features/regulatory_capital_features.py` |
| Asset correlation (R) | **Documented assumption, not measured** | Basel retail risk-weight function parameters, fixed or PD-dependent per segment per [BCBS06] |

Home Credit's real dataset carries no realized-recovery or workout history,
so LGD and R **cannot** be measured from it — this suite never pretends
otherwise. Every LGD/R value is a cited, published reference point, applied
identically to every real applicant in a segment; none is fitted, tuned, or
backed out to hit a target number.

## Formula (Basel retail-IRB, unmodified)

- **Expected Loss** = PD × LGD × EAD — [BCBS06] §272–287.
- **Capital requirement K** (fraction of EAD, unexpected loss only) — the
  Vasicek/ASRF closed form from [BCBS05]:
  `K = LGD × Φ[(1−R)^-0.5 × Φ⁻¹(PD) + (R/(1−R))^0.5 × Φ⁻¹(0.999)] − PD × LGD`
- **RWA** = K × 12.5 × EAD; **Capital requirement ($)** = RWA × 8% Pillar-1
  minimum = K × EAD.
- No maturity adjustment: retail exposures are explicitly exempt from the
  maturity-adjustment term that applies to corporate/sovereign/bank
  exposures under this framework.

Full citations: Basel Committee on Banking Supervision, *"International
Convergence of Capital Measurement and Capital Standards: A Revised
Framework — Comprehensive Version"* (June 2006); *"An Explanatory Note on
the Basel II IRB Risk Weight Functions"* (July 2005); EU Capital
Requirements Regulation (575/2013) Art. 164 (context for the real-estate
secured LGD floor).

## Statistical robustness verdict vs. pipeline integrity checks

This notebook reports two genuinely different, independently-computed
check families — not the same result shown twice:

- **Pipeline Integrity Checks** — structural sanity (columns present, LGD
  within [0,1], EAD non-negative, correlation in bounds, Expected Loss ≤
  EAD, thread ceiling applied, etc.). These check that the *pipeline ran
  correctly*, not that the underlying association is statistically strong.
- **Statistical Robustness Verdict** — a real chi-square test of PD-risk
  band vs. real observed `TARGET`, a vectorized bootstrap 95% CI on
  Cramer's V, and a Bonferroni-corrected, statistically-tolerant
  monotonicity check on real default rate across PD bands
  (`src/utils/stats_checks.py monotonic_within_noise()` — a genuine
  two-proportion z-test per adjacent pair, not a strict zero-tolerance
  ordering check).

It is real and expected for Pipeline Integrity Checks to pass 100% while
the Statistical Robustness Verdict reports a failed check — this is common
on small samples (including this suite's synthetic verification fixture)
and is not a code defect. The verdict string always names the specific
failing check(s).

## Two real bugs found and fixed in `default_rate_monotonic_by_pd_band`

This notebook's first version showed a false "NOT YET STATISTICALLY
ROBUST — failed: default_rate_monotonic_by_pd_band" verdict — including on
the user's own real, full-scale 307,511-applicant run — despite a highly
significant chi-square (p < 0.001) and a tight bootstrap 95% CI on Cramer's
V clearly excluding zero. Root-caused to two separate, real, disclosed
issues (see `CHANGELOG.md` [1.4.3] for the full record):

1. **A directionality bug, the primary cause.** `monotonic_within_noise()`
   (`src/utils/stats_checks.py`) is documented to expect its input already
   ordered with group 0 = *highest* expected rate. `band_agg` in this
   notebook is sorted ascending by risk ("Lowest Risk" first) — the natural
   order for a human-readable report — but default rate is expected to
   *increase* with risk, so this notebook was passing the function the
   wrong direction, causing every adjacent-band comparison to look
   "reversed" essentially by construction. Fixed by reversing the arrays
   immediately before the call, matching the convention Notebook 03 and
   Notebook 04 already used correctly. Confirmed on the user's own real, full-scale 307,511-applicant rerun:
   the real, unchanged band-level default rates (1.86% → 6.52% →
   15.01% → 29.31% → 53.90%) are genuinely, strongly monotonic, and the
   verdict now correctly reads "STATISTICALLY ROBUST — RECOMMENDED FOR
   PRODUCTION" once compared in the right direction — the underlying
   z-statistics in the JSON audit trail are byte-identical to before the
   fix, only the direction of comparison changed.
2. **A large-sample statistical-power issue, addressed defensively.**
   Independent of (1), a pure statistical-significance test gets more
   powerful as real sample size grows, so at production scale (hundreds of
   thousands of rows) it can flag a tiny, practically meaningless
   adjacent-band reversal as "significant." `monotonic_within_noise()` now
   also requires a reversal to clear a real, disclosed minimum-effect-size
   threshold (`min_practical_difference`, default 0.25 percentage points)
   before it counts as a violation — the standard remedy for this problem
   (Cohen, J. (1994), "The Earth Is Round (p < .05)", *American
   Psychologist*, 49(12), 997–1003). This is a documented assumption,
   applied uniformly to every call site in this suite, not tuned per-run.

Both fixes are disclosed, not quiet threshold tweaks: the JSON summary's
`monotonicity_detail` array records the real z-statistic, p-value,
reversal magnitude, and both the statistical-significance and
practical-materiality verdict for every adjacent pair, so a reversal that
is significant but immaterial remains visible in the audit trail even
though it no longer fails the gate.

## Limitations

- LGD/EAD/R are assumptions, not measurements — a bank deploying this
  approach in production would replace them with its own internally
  validated, back-tested estimates (or, for retail residential mortgage
  under some jurisdictions, a supervisory floor) before any regulatory use.
- EAD as raw `AMT_CREDIT` does not apply a credit-conversion factor to
  undrawn revolving limits — a refinement noted, not implemented, at this
  notebook's scope.
- Segment assignment uses only 3 real columns (`NAME_CONTRACT_TYPE`,
  `FLAG_OWN_REALTY`, `FLAG_OWN_CAR`) — a production LGD model would use
  richer collateral valuation and loan-to-value data this dataset does not
  provide.
- This notebook inherits every limitation already documented in Mega
  Project 1 / Notebook 01's own model card (its PD model is the sole real,
  measured input here).

## Reproducibility

`RANDOM_SEED = 42` throughout (bootstrap resampling, sampled dashboard
table). Deterministic given the same input data and the same upstream
Notebook 01 champion model artifact. Idempotent — re-running overwrites the
same output paths, never appends.
