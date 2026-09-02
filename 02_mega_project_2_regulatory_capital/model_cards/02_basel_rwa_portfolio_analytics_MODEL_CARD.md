# Model Card — Problem 2: Basel RWA Portfolio Analytics

Notebook: `notebooks/02_basel_rwa_portfolio_analytics.ipynb`

## This is not a model — it's a pure analytical layer

This notebook trains nothing and computes no new PD, LGD, or EAD. It loads
Notebook 01's already-computed, already-disclosed real per-applicant
Expected Loss / RWA / capital-requirement output (hard dependency — fails
loudly if Notebook 01 has not been run yet) and joins it with real
application-level segment columns (`NAME_INCOME_TYPE`,
`NAME_EDUCATION_TYPE`, `NAME_CONTRACT_TYPE`, `REGION_RATING_CLIENT`) purely
for cross-tabulation. Every dollar figure here traces back to Notebook 01's
real PD × documented LGD × real EAD computation — see that problem's model
card for the assumption sourcing.

## What it reports

**RWA density** (total RWA ÷ total EAD) — the standard Basel Pillar 3
disclosure metric banks use to compare capital intensity across portfolios
of different size — computed per PD risk band and per real segment cut,
alongside real default rate and total capital requirement for the same
cuts.

## A real statistical bug found and fixed while building this notebook

RWA density is a **ratio, not a proportion** — under the Basel K() formula,
RWA can legitimately exceed EAD for high-risk/high-LGD segments (this suite's own real, full-scale 307,511-applicant rerun shows the
"High Risk" and "Highest Risk" PD bands at 112.4% and 107.2% density
respectively). The first version of this notebook fed RWA density into
`monotonic_within_noise()` (a two-proportion z-test, valid only for values
bounded in [0, 1]) and it threw a `math domain error` on execution — a real
bug caught by this suite's own verification protocol (fixture → real
execution → 0 errors required), not something that slipped through. Fixed
by reporting RWA-density ordering descriptively (a real, computed fact) but
deliberately excluding it from the statistically-gated
`validation_checks` family — gating a ratio with a test built for
proportions would have been statistically invalid, not just imprecise.
Real default rate *is* a true proportion and is still gated normally. Full
record in the root `CHANGELOG.md`.

## A second real bug found and fixed: the same directionality issue as Notebook 01

Independent of the RWA-density bug above, this notebook's `default_rate_
monotonic_by_pd_band` check (and its descriptive RWA-density ordering
comparison) had the same root cause as Notebook 01's: `band_agg` is sorted
ascending by risk, but `monotonic_within_noise()` expects its input ordered
with the highest expected rate first. Both were feeding the ascending-order
arrays through unreversed, and the density comparison operator was pointed
the wrong way for that same ascending order. Fixed by reversing before the
`monotonic_within_noise()` call and flipping the density comparison to
`<=`. Confirmed via real re-execution on the user's own real, full-scale
307,511-applicant rerun: the verdict
flips from "NOT YET STATISTICALLY ROBUST" to "STATISTICALLY ROBUST —
RECOMMENDED FOR PRODUCTION" against the same underlying, unchanged data —
see `CHANGELOG.md` [1.4.3] and Notebook 01's model card for the full
disclosure, including the separate large-sample practical-materiality
threshold added to `monotonic_within_noise()` at the same time.

## Statistical robustness verdict vs. pipeline integrity checks

Same two-tier pattern as every notebook in this suite: **Pipeline
Integrity Checks** (structural — segment columns present, RWA density
finite, chi-square p-value in bounds) vs. **Statistical Robustness
Verdict** (chi-square significance, bootstrap CI on Cramer's V, real
default-rate monotonicity by PD band). Passing one does not imply the
other passed — the verdict string names the specific failing check(s).

## Limitations

- Segment cuts are limited to 4 real application-level columns; a richer
  concentration view (e.g. geography, vintage) would need columns this
  scope did not include.
- RWA density figures inherit every limitation already documented in
  Notebook 01's model card (LGD/correlation are documented assumptions,
  not measured).

## Reproducibility

`RANDOM_SEED = 42` (bootstrap resampling only). Idempotent — re-running
overwrites the same output paths.
