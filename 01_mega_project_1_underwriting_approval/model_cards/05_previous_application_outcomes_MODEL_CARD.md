# Model Card — Problem 5: Previous Application Outcomes

Notebook: `notebooks/05_previous_application_outcomes.ipynb`
Service: none — this is a portfolio-level statistical analysis, not a
per-applicant prediction, so there is no scoring API for it.

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

This notebook analyzes `previous_application.csv` — applicants' prior loan
application history at Home Credit — using descriptive statistics and a
real chi-square test of association. There is no classifier and no
`.joblib` bundle.

## What it computes

- A real decision funnel from `NAME_CONTRACT_STATUS` (approved / refused /
  cancelled / unused offer) distribution.
- A real reject-reason breakdown within refused applications.
- Real post-approval drop-off (offer-utilization rate).
- A real cohort breakdown by client type and channel.
- **Cross-validation against Notebook 01's PD**: checks whether prior
  application outcome is really associated with current default
  probability, using a real chi-square test (`scipy.stats.chi2_contingency`)
  and Cramer's V effect size — reported honestly either way, including
  when the result is *not* statistically significant.
- A second chi-square test of whether current-application outcome is
  associated with client type, with the same real statistic/p-value/effect
  size reporting.
- A real relative-recency trend from `DAYS_DECISION`.
- **Bootstrap robustness check** on the chi-square association: this is the
  section that was performance-hardened during this project's build (see
  `BENCHMARKS.md` — a ~3,000x speedup was achieved by replacing a per-
  resample `pandas.crosstab` rebuild with a mathematically equivalent
  direct `numpy.random.Generator.multinomial` draw from the same real
  empirical joint-cell distribution; the statistic reported is the same
  real quantity, not an approximation of it).

## Statistical robustness verdict vs. pipeline integrity checks

Same distinction as Problem 4's model card (`04_repayment_capacity_analysis_MODEL_CARD.md`)
and `CHANGELOG.md` entry [1.0.1] — this notebook's Statistical Robustness
Verdict (chi-square significance, bootstrap-CI-excludes-zero on Cramer's V,
funnel-distribution stability) is a separate, stricter gate from its
Pipeline Integrity Checks. A failed `chi_square_significant` here on a
small or noisy sample is a real, honest result (the association between
prior outcome and current risk wasn't statistically significant on this
run) — not a code defect, and not inconsistent with all integrity checks
passing.

## Why there's no scoring service for this problem

Every output here is a population-level statistic (a chi-square p-value, a
funnel percentage, a cohort breakdown) — there is no single-record
prediction to expose behind an API endpoint. Building a "service" that
returns a portfolio-level statistic on every request would either be
static (misleadingly implying it's live) or require re-running the full
notebook per request (not a sensible API design). This is a genuine scope
boundary, not an omission.

## Limitations

- Association (chi-square/Cramer's V) is not causation — a statistically
  significant link between prior outcome and current PD does not by itself
  justify an automated decision rule; it's evidence for further
  underwriting-policy review.
- `previous_application.csv` history is only available for applicants who
  have a prior Home Credit application; first-time applicants are outside
  this notebook's population by construction.

## How to reproduce

Run `notebooks/05_previous_application_outcomes.ipynb` end-to-end. (Running
Notebook 01 first is recommended so the cross-validation-against-PD section
has real PD values to check against.)
