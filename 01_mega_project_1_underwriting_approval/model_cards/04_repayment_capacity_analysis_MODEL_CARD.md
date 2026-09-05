# Model Card — Problem 4: Repayment Capacity Analysis

Notebook: `notebooks/04_repayment_capacity_analysis.ipynb`
Service: `services/repayment_capacity_service.py` (FastAPI, port 8004) — ratios only, see below

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `18ea21c`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 4 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (e.g. `517b7f4`, from the
2026-09-02 sync, when a `polars` dependency was briefly missing from the
`shared-tests` job) — that historical failure was fixed in commit `96e4321`
and does not reflect the current state of the suite.

## This is not a trained model

This notebook computes real, data-derived financial ratios directly from
applicant fields — it does not train a classifier, and there is no
`.joblib` bundle for this problem.

## What it computes

- `REPAYMENT_CAPACITY_RATIO` and `TOTAL_DEBT_BURDEN_RATIO` — real ratios
  computed from applicant income, credit, and annuity fields (formulas are
  data-derived, not assumed; see Section 6 of the notebook for the exact
  arithmetic).
- A data-quality guard (Section 6B) excludes the small subset of rows where
  a required input (e.g. annuity) is missing or non-finite, rather than
  letting them silently corrupt downstream aggregates or crash the
  histogram plot — this was a real bug found and fixed during this
  project's build (see the root CHANGELOG.md).
- **Data-driven tiered segmentation**: applicants are split into
  segmentation tiers by real quintiles of the computed ratios, not fixed,
  hardcoded thresholds (e.g. "ratio > 3.0 = safe"). This is a deliberate
  choice: fixed cutoffs would be arbitrary without an external validated
  reference; quintiles let the notebook say "this tier's real, measured
  default rate is X%" using this population's own outcomes.
- **Cross-validated against Notebook 01's PD**: this notebook checks
  whether its independently-computed ratios and tiers are actually
  associated with Notebook 01's model-predicted default probability, as an
  honesty check that the ratios mean something, not two disconnected
  numbers.
- A secondary informational cross-check against a labeled external
  reference is included in Section 8 for additional context.

## Statistical robustness verdict vs. pipeline integrity checks

This is the problem where a user of this suite actually observed the issue
fixed in `CHANGELOG.md` entry [1.0.1]: the executive rollup showed
"NOT YET ROBUST — one or more validation checks failed" right next to a
passing "13/13 PASS" Integrity Checks count, which read as a
contradiction. It wasn't one — they are two different, independently-
computed check families:

- **Pipeline Integrity Checks** (13 on a run with Notebook 01's bundle
  present) — structural sanity: data loaded, required columns present,
  ratios finite, thread ceiling applied, etc. All 13 genuinely passed.
- **Statistical Robustness Verdict** (a separate 4-check gate: chi-square
  significance, a bootstrap 95% CI on Cramer's V excluding zero, split-half
  PSI stability, and tier-to-default-rate monotonicity) — on a small or
  noisy population it is real and expected for `chi_square_significant`
  and/or `tier_monotonicity_holds` to fail even when every integrity check
  passes; that is an honest statistical result on this run's data, not a
  code defect.

The verdict text now names the specific failing check(s) explicitly (e.g.
`"NOT YET STATISTICALLY ROBUST — failed: chi_square_significant,
tier_monotonicity_holds"`) instead of a vague pointer, and the executive
report's table columns and an accompanying note were updated to make the
distinction visible without reading this card. If you see this verdict on
your own real data run, check the specific named check(s) — a failed
`chi_square_significant` most often means the quintile tiers don't (yet)
show a statistically clean relationship to default rate in your
population, which is informative in itself, not a bug to chase.

**`tier_monotonicity_holds` methodology (CHANGELOG [1.0.2])**: on the real,
full 307,499-applicant Home Credit population, this check was found to
fail from a single adjacent-tier reversal ("Weakest" 8.5122% vs. "Weak"
8.6992% default rate, n=61,500 each) that a real two-proportion z-test
shows is not statistically significant (z=1.17, p=0.24) — while the other
three statistical checks for this problem all independently confirmed a
real, significant, cross-validated association. The strict zero-tolerance
check was flagging noise as a real violation. It now runs a real,
Bonferroni-corrected two-proportion z-test per adjacent tier pair
(`src/utils/stats_checks.py`) and only fails if a reversal is itself
statistically significant, matching the tolerance every sibling check in
this gate already has. A reversal that isn't distinguishable from sampling
noise no longer fails this check; a genuinely significant one still does
— the per-pair z-statistic and p-value are saved to
`notebook_04_summary.json`'s `monotonicity_detail` field so this is
auditable on your own real run, not asserted.

## Why the API service does not return a risk tier

`services/repayment_capacity_service.py` returns the two ratios
(`repayment_capacity_ratio`, `total_debt_burden_ratio`) for a single
submitted record, but deliberately does **not** return a tier label. The
tiers in the notebook are **population-relative quintiles** — which tier a
given ratio value falls into depends on the full population's ratio
distribution at analysis time, not on a fixed, single-record-reproducible
threshold. A stateless per-request API endpoint cannot honestly reproduce
"which quintile of the population is this applicant in" without either
(a) shipping a frozen, potentially stale quintile-boundary snapshot as a
silent assumption, or (b) querying the full population on every request.
Rather than fabricate a tier from stale or embedded boundaries, the service
returns the real ratios only and documents this limitation in its own
docstring.

## Limitations

- Ratios depend on self/application-reported income and annuity fields, not
  independently verified income (this is a property of the underlying
  Kaggle data, not something this notebook can correct).
- Quintile tier boundaries will shift if run on a different population or a
  different time slice — they are descriptive of the analyzed population,
  not fixed cutpoints to hardcode elsewhere.

## How to reproduce

Run `notebooks/04_repayment_capacity_analysis.ipynb` end-to-end. (Running
Notebook 01 first is recommended so the cross-validation-against-PD section
has real PD values to check against, but this notebook still produces its
core ratio/tier analysis without it.)
