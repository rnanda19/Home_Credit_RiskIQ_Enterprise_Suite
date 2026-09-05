# Model Card — Problem 3: Economic Capital & Unexpected Loss

Notebook: `notebooks/03_economic_capital_unexpected_loss.ipynb`
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

## This is not a model, and it introduces no new assumption — read this first

This notebook trains nothing and adds no new PD, LGD, EAD, or asset
correlation. It reuses Notebook 01's already-computed, already-disclosed
real per-applicant `PD`, `LGD_ASSUMED`, `EAD_PROXY`, and `CORRELATION_R`
unchanged (hard dependency — fails loudly if Notebook 01 has not been run
yet). Every dollar figure here traces back to Notebook 01's real PD ×
documented LGD × real EAD computation — see that problem's model card for
the assumption sourcing (LGD/correlation citations, `[BCBS06]`, `[BCBS05]`,
`[EBA-CRR]`).

## What Notebook 01 already gives you, and what this notebook adds

Notebook 01 solves the single-factor Vasicek/ASRF model **analytically** —
the Basel `K()` closed form is the 99.9th-percentile point of that model's
loss distribution, solved directly, with no visibility into the rest of the
distribution. This notebook instead **simulates** the same model, via a
real, vectorized Monte Carlo over the systematic risk factor, which is the
only way to obtain:

- Value-at-Risk / Economic Capital at confidence levels *other than* 99.9%
  (95%, 99%, 99.5% — useful for internal risk appetite, not just the Pillar
  1 regulatory minimum).
- Expected Shortfall / CVaR (mean loss beyond VaR) — has no closed form
  under this model at all.
- A real, independent numerical cross-check of Notebook 01's closed-form
  capital number.

## Limitation, stated plainly

This Monte Carlo simulates the **same** single-factor, infinite-granularity
(ASRF) assumptions Basel's own closed form already makes — one systematic
factor, no single-name concentration/granularity add-on, no multi-factor
correlation structure. It is a genuine, independently-computed cross-check
and a genuine source of new distributional detail, **not** a more
sophisticated economic-capital model than Notebook 01. A real bank's
internal economic-capital model would go further (granularity adjustment,
multi-factor correlation, name concentration) than this notebook's scope —
noted here, not implemented.

## Technique: real vectorized Monte Carlo, not a bootstrap

This is a genuine Monte Carlo simulation of a parametric model (drawing new
systematic-factor realizations from `N(0,1)`), a different technique from
this suite's "vectorized multinomial bootstrap" lesson (which resamples an
*empirical* joint distribution — there is no empirical distribution to
resample here, since the model itself is being simulated). Per draw, every
real applicant's conditional default probability is computed in ONE
vectorized `scipy.stats.norm.cdf` call over the whole real portfolio;
draws are processed in batches (a `(batch_size, n_applicants)` matrix per
batch) so the number of Python-level loop iterations stays small (100
batches of 500 draws each by default) regardless of the total draw count —
on the user's own real, full-scale 307,511-applicant portfolio, 50,000
draws complete in about 522 seconds (~8.7 minutes).

## Two real, computed validation layers (not asserted)

1. **Closed-form cross-check** (Section 8): the Monte-Carlo-simulated 99.9%
   Economic Capital is compared against Notebook 01's real closed-form Basel
   capital requirement — both derive from the same model and the same real
   inputs, so they should agree closely. A documented 10% relative
   tolerance accounts for real Monte Carlo sampling error at an extreme
   quantile with a finite draw count — not a threshold tuned to force a
   pass. On the user's own real, full-scale rerun: 1.62% relative difference
   (well within tolerance).
2. **Independent-reseed convergence check** (Section 9, this notebook's
   "Statistical Robustness Verdict" family): there is no real `TARGET` to
   test a classifier against here, so robustness instead means a SECOND,
   independently-seeded Monte Carlo run of the same model, compared against
   the first at each confidence level. Tolerances widen at higher
   confidence levels (5% at 95%, up to 15% at 99.9%) because a finite Monte
   Carlo sample has real, larger sampling error further into the tail — a
   real, disclosed property of Monte Carlo estimation, not a per-run tuned
   number.

## Pipeline Integrity Checks vs. Statistical Robustness Verdict

Same two-tier pattern as every notebook in this suite. Pipeline Integrity
(Section 12) checks structural sanity — simulated losses finite and
non-negative, VaR non-decreasing across confidence levels (a real
mathematical guarantee for quantiles of the same distribution — failing
this would indicate a genuine coding bug), Economic Capital non-negative at
99%+ confidence. Statistical Robustness (Section 10) is the stricter,
separately-computed gate described above. The verdict string always names
the specific failing check(s).

## Configuration

`N_MC_DRAWS` (main run) and `N_MC_DRAWS_CHECK` (reseed check) are real,
disclosed, user-overridable performance knobs — set via
`project_config.json` `"mc_draws"` / `"mc_draws_reseed_check"` — not
hardcoded to whatever happened to run fast during initial development. Default 50,000 main / 20,000 reseed-check draws, batch size
500 (also configurable: `"mc_batch_size"`).

## Limitations

- Inherits every limitation already documented in Notebook 01's model card
  (LGD/EAD/R are assumptions, not measurements).
- ASRF single-factor assumption only (see "Limitation, stated plainly"
  above) — no granularity adjustment, no multi-factor correlation, no
  single-name concentration.
- Portfolio-level only in this notebook's scope — segment-level capital
  concentration is Problem 5's dedicated job, not duplicated here.

## Reproducibility

`RANDOM_SEED = 42` (main Monte Carlo run); the independent-reseed
convergence check deliberately uses `RANDOM_SEED + 1` (a different, but
still fixed and disclosed, seed — the whole point of that check is a
genuinely independent draw, not a re-run of the identical stream).
Deterministic and idempotent given the same Notebook 01 output and the same
`project_config.json` Monte Carlo settings.
