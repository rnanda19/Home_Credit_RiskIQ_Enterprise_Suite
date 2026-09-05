# Model Card — Problem 5: Capital Concentration by Segment

Notebook: `notebooks/05_capital_concentration_by_segment.ipynb`
Hard dependency (not owned by this notebook): `../decision_engine/artifacts/notebook_01_capital_scores.csv`

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This is not a model — it introduces no new PD/LGD/EAD/correlation value

This notebook trains nothing and re-scores nothing. It reuses Notebook 01's
already-computed, already-disclosed real per-applicant `CAPITAL_REQUIREMENT`
and `EAD_PROXY` unchanged, joined with real application-level segment
columns (`NAME_INCOME_TYPE`, `NAME_EDUCATION_TYPE`, `NAME_CONTRACT_TYPE`,
`REGION_RATING_CLIENT`) already used by Notebook 02 — plus Notebook 01's
own `CAPITAL_SEGMENT` (the LGD-collateral-proxy segment), for 5 real
dimensions in total.

## Why this is a genuine, not redundant, addition to Problem 1

Notebook 01's Basel closed-form capital charge (the single-factor
Vasicek/ASRF model) rests on an infinite-granularity assumption: it treats
the portfolio as made of infinitely many infinitesimally small exposures,
so idiosyncratic/name concentration risk is fully diversified away and
charged **zero** capital by construction [BCBS05]. Basel's own Pillar 2
framework requires banks to separately assess concentration risk that
Pillar 1 deliberately does not price. This notebook is that separate
assessment — a real Herfindahl-Hirschman Index (HHI) of capital
concentration across every real segment/geography dimension this dataset
provides.

## What HHI means here, precisely

For each dimension, HHI = Σ(capital share of segment *i*)², reported both
as a fraction (0–1) and on the conventional 0–10,000-point scale
(`hhi_points = hhi_fraction × 10,000`). Also reported: `effective_n_segments
= 1 / hhi_fraction` (the number of *equally sized* segments that would
produce the same HHI — an intuitive "effective diversification count").

Interpretive bands (**a disclosed, borrowed convention, not a
Basel-mandated portfolio threshold**): the U.S. DOJ/FTC Horizontal Merger
Guidelines bands — HHI < 1,500 Unconcentrated, 1,500–2,500 Moderately
Concentrated, > 2,500 Highly Concentrated — widely borrowed in
credit-portfolio concentration-risk practice, stated plainly here as
borrowed, never implied to be a regulatory capital add-on.

## Advanced error tackling applied

- **Hard dependency** checked by actual required columns present
  (`SK_ID_CURR`, `CAPITAL_SEGMENT`, `CAPITAL_REQUIREMENT`, `EAD_PROXY`) in
  Notebook 01's output, not just file existence (`LESSONS_LEARNED.md` #4).
- **Real cross-check #1 — sum-to-total identity**: every dimension's
  segment capital totals are checked to sum back to the real portfolio
  total to within 1e-9 relative difference. A join or groupby bug (a
  dropped applicant, a mismatched key) would show up immediately as a
  failed check here, not as a silently wrong number (`LESSONS_LEARNED.md`
  #6).
- **Real cross-check #2 — mathematical bounds**: HHI (as a fraction) is
  checked to fall within its real mathematical bounds `[1/N, 1]` for a
  dimension with `N` segments — the lower bound is a perfectly equal
  split, the upper bound is total concentration in one segment. A
  computation error producing an out-of-bounds HHI would raise
  immediately.
- **No `monotonic_within_noise()` risk in this notebook, by construction**:
  the directionality bug that hit Notebooks 01 and 02 (`CHANGELOG.md`
  [1.4.3]) only applies to checks with an *expected order* across bands.
  Concentration analysis compares unordered categorical segments — there
  is no ordering convention to get backwards here (`LESSONS_LEARNED.md`
  #2 does not apply by construction, not by omission).

## Swift processing

One vectorized `pandas` groupby-aggregate per real dimension — the same
pattern already proven fast in Notebook 02 (1.2 seconds on the user's real
307,511-applicant portfolio) — never a per-applicant Python loop.

On the same user's own real, full-scale 307,511-applicant portfolio, all
5 dimensions computed in 0.58 seconds (well under 1 second).

## Concentration Validation Verdict vs. Pipeline Integrity Checks

Deliberately NOT named "Statistical Robustness Verdict" like the
TARGET-based notebooks elsewhere in this suite (Notebooks 01/02) or even
"Scenario Validation Verdict" like Notebook 04. HHI is a deterministic
concentration measure computed directly from real capital shares — there
is no random sampling (unlike Notebook 03) and no hypothetical scenario
(unlike Notebook 04) to validate against a real TARGET or a mechanics
check. This tier — "Concentration Validation Verdict" — validates that the
computation itself is mathematically correct and internally consistent
(the two cross-checks above), stated explicitly as its own kind of
validation rather than forcing an ill-fitting statistical-significance
test onto a metric that has none to test.

## Limitations

- HHI is a portfolio-structure metric, not a capital number — it does not
  itself produce a dollar capital add-on. Translating a "Highly
  Concentrated" finding into an actual Pillar-2 capital add-on requires a
  granularity adjustment methodology (e.g., Basel's own GA formula) that
  is out of scope for this notebook and not built here.
- `REGION_RATING_CLIENT` is the only real geography proxy in this
  dataset — Home Credit's real data has no state/province/city field, so
  true geographic concentration (as opposed to a coarse 3-level region
  rating) cannot be assessed beyond what this column provides.
- The DOJ/FTC interpretive bands are a borrowed convention from market
  concentration (antitrust) analysis, not a credit-portfolio-specific or
  regulatory-mandated threshold — disclosed above, not implied.
- Segment definitions are exactly Notebook 01's and Notebook 02's existing
  segment columns — this notebook does not introduce or validate any new
  segmentation scheme of its own.

## Reproducibility

Deterministic — no random sampling anywhere in this notebook. Idempotent:
re-running overwrites the same output paths given the same Notebook 01
output and the same real `application_train.csv`.
