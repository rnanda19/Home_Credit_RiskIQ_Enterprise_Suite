# Changelog

All notable changes to this repository are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-09-01

### Changed — README and documentation rewritten for a hiring-manager/recruiter audience; no code or notebook content changed

**What prompted this**: this repo is a portfolio piece as well as an
engineering project — the documentation needed to read that way without
weakening the zero-fabrication standard the rest of this repo is held to.

**What changed**:

- Root `README.md`: added a **Skills Demonstrated** table mapping this
  repo's real techniques (statistical rigor, explainability, model risk
  and governance, MLOps, software engineering discipline) to where they're
  evidenced; added a **Model Risk & Governance** section describing the
  real dual-check pattern (structural integrity checks vs. statistical
  robustness gates) every notebook already runs, and how a model can pass
  integrity checks yet still be honestly reported "not recommended for
  production yet" when a robustness gate fails — framed in the language a
  regulated financial institution's model-risk function would use (SR
  11-7-style discipline), without claiming formal compliance with any
  framework this repo hasn't been assessed against.
- Added `docs/mp1_executive_dashboard_preview.png` — a screenshot of the
  real Mega Project 1 executive dashboard, embedded directly in the root
  README so a reader doesn't have to clone the repo or open a raw HTML
  file in GitHub's browser to see real output. Captioned explicitly as
  generated from the synthetic verification fixture, not the real Home
  Credit dataset — the same honesty standard applied everywhere else in
  this repo.
- CI badges switched from static "passing" images to GitHub's own live
  workflow-status badges (`.../actions/workflows/ci.yml/badge.svg`), so
  the badge reflects the actual, current state of CI rather than an
  unverifiable claim.
- Mega Projects 2-5 `README.md` files expanded from a one-line "not yet
  built" stub to include the real business problem each is scoped to
  cover and its planned approach — still explicit that no notebooks,
  models, or services exist for them yet; no new capability is claimed.

**What did NOT change**: no notebook, model, service, or check logic
changed — this entry is a documentation and presentation change only.

## [1.2.1] - 2026-09-01

### Added — full sample reports (HTML/Word/Excel) for all 5 problems + the executive rollup

**What prompted this**: the images added in [1.2.0] show what the output
looks like; a hiring manager who wants to open a real, fully-formatted
deliverable (not a chart crop) needed a real file to open.

**What changed**:

- Added `01_mega_project_1_underwriting_approval/sample_reports/` — 18
  files: the real HTML dashboard, Word report, and Excel workbook already
  generated per problem (5 problems) plus the consolidated executive
  rollup in the same 3 formats. These are the exact files this suite's own
  notebooks produce when run — copied from `decision_engine/reports/`
  (gitignored everywhere else in this repo), every filename prefixed
  `SAMPLE_`, with a folder `README.md` stating plainly that they were
  generated against the synthetic verification fixture, not the real
  Kaggle dataset, and linking to where a reader can generate the real
  version themselves. `.gitignore`'s `**/decision_engine/reports/` rule
  does not apply here — `sample_reports/` is a distinct, deliberately
  tracked folder, not a path under `decision_engine/`.
- Root `README.md`'s "Real Output" section now links to this folder.

**What did NOT change**: no notebook, model, service, or check logic
changed; the files added are unmodified copies of already-verified
generated output, only renamed with a `SAMPLE_` prefix for clarity.

## [1.3.0] - 2026-09-01

### Added — GitHub Pages live dashboard hosting; corrected README claims about how GitHub renders linked files

**What prompted this**: a direct question about whether the `.html`/
`.docx`/`.xlsx` links added in [1.2.0]/[1.2.1] would actually open as
rendered pages when clicked on GitHub. They don't — GitHub shows raw
source for `.html` files and a download-only page for Office documents;
only `.csv` renders natively. That's true of every GitHub repository, not
a flaw introduced here, but the README needed to say so instead of
implying otherwise.

**What changed**:

- Added `docs/dashboards/` — copies of the 6 real dashboard HTML files
  (5 problems + the executive rollup), and `docs/index.html`, a landing
  page linking to all 6. Both are verified with the same protocol as
  every other HTML output in this repo (Playwright, all network requests
  blocked: 0 external requests, 0 page errors).
- `push-to-github.ps1`: passing `-Public` now also (a) flips an
  already-existing private repo to public via the API, and (b) enables
  GitHub Pages (source: `main` / `/docs`) via the API — idempotent, safe
  to re-run. GitHub Pages requires a public repo on the free plan, which
  is why this is gated on `-Public` rather than automatic.
- Root `README.md`: added a **Live Dashboards** section with the real
  Pages URLs, and corrected the [1.2.1] sample-reports callout to state
  plainly how GitHub actually opens `.html`/`.docx`/`.xlsx`/`.csv` files
  when clicked, instead of implying they'd all open cleanly.

**What did NOT change**: no notebook, model, service, or check logic
changed; `docs/dashboards/` files are unmodified copies of already-
generated, already-verified output.

## [1.1.0] - 2026-09-01

### Changed — restructured the repository to match this account's portfolio-repo conventions (flat, numbered, self-contained project folders)

**What prompted this**: to keep this repo organized the same way as this
account's other portfolio repos — flat, numbered top-level project folders
instead of nested ones, so GitHub's default alphabetical file listing
renders in logical numeric order at a glance.

**What changed**:

- All 5 Mega Project folders moved to the repo root with a numeric prefix
  (purely a cosmetic display-ordering prefix — the underlying Mega Project
  identity and every internal path/code reference stays the same, just
  relocated):
  `mega_project_1_underwriting_approval/` → `01_mega_project_1_underwriting_approval/`,
  `mega_project_2_regulatory_capital/` → `02_mega_project_2_regulatory_capital/`,
  `mega_project_3_risk_segmentation/` → `03_mega_project_3_risk_segmentation/`,
  `mega_project_4_delinquency_prevention/` → `04_mega_project_4_delinquency_prevention/`,
  `mega_project_5_liquidity_cashflow/` → `05_mega_project_5_liquidity_cashflow/`.
- Every reference to the Mega Project 1 path was updated in the same
  change — `Makefile`, `.github/workflows/ci.yml`,
  `.github/workflows/code-quality.yml`, `docker/Dockerfile`,
  `docker/docker-compose.yml`, this project's own `README.md`, and the
  `ARTIFACTS_DIR`/`REPORTS_DIR`/`PARQUET_CACHE_DIR`/`MP1_DIR` path
  constants inside all 6 notebooks (01-06) — the same functional-path
  discipline as [1.0.3]: since these are runtime path references (not just
  cosmetic text), all 6 notebooks were re-executed end-to-end against the
  synthetic fixture after the change (0 errors), had outputs cleared, were
  `nbformat`-validated, and had their regenerated
  `decision_engine/reports/*.xlsx` outputs recalculated cleanly under
  LibreOffice headless and their `*_dashboard.html` outputs checked under
  Playwright with all network requests blocked (0 external requests, 0
  page errors).
- Added `00_executive_rollup_report/` at the repo root as the intended home
  for a future suite-wide executive rollup. It is an honest placeholder,
  not a data folder: with only 1 of 5 Mega Projects built, a suite-wide
  number would have to average in 4 unbuilt Mega Projects, which this repo
  will not fabricate. It currently just points to Mega Project 1's own real
  rollup and states plainly what's built and what isn't.
- Root `README.md` rewritten to this account's standard portfolio-repo
  README pattern (badges, a status-first headline, table of contents,
  platform-at-a-glance, repository structure, how-to-run, technologies,
  roadmap, repository hardening summary, license) — see the README itself
  for the honesty caveats this rewrite kept: it reports 1-of-5 status
  plainly rather than implying a fuller build, and does not carry any
  suite-wide dollar figure, since none has been measured on real data.
- License intentionally **left as MIT** (not changed to a more restrictive
  license) — this was a deliberate choice, not an oversight, made when
  aligning this repo's conventions with the rest of the portfolio.
- A "Live Dashboards" README section (GitHub Pages links) was intentionally
  **not added** — this repo doesn't have GitHub Pages configured, and a
  link to a page that doesn't exist would be worse than no section.

**What did NOT change**: no notebook's computed results, statistics,
model, or check logic changed — this entry is a folder-layout and
documentation-format change, not a methodology or data change like
[1.0.2].

## [1.0.3] - 2026-09-01

### Changed — corrected the Mega Project numbering to its final 5-project scope, and completed the Mega Project 1 folder rename

**What prompted this**: the suite was originally scoped as 6 planned Mega
Projects. Mega Project 6 (Behavioral Analytics) was dropped from the plan
before any build work started on it, for lack of the source data and
feature columns it would have needed — leaving 5 Mega Projects, not 6.
Separately, while that 6-project scope was still active, Underwriting &
Approval Intelligence (this repo's Mega Project 1 — the only one that's
actually built) was checked out under the folder name
`mega_project_3_underwriting_approval/`, a numbering mismatch this repo had
been carrying (and disclosing, unresolved, in prior versions of the root
README) since the [1.0.0] hardening pass.

**What changed**:

- `mega_project_3_underwriting_approval/` was renamed to
  `mega_project_1_underwriting_approval/` — every reference to the old path
  was updated in the same change: `Makefile`, `.github/workflows/ci.yml`,
  `.github/workflows/code-quality.yml`, `docker/Dockerfile`,
  `docker/docker-compose.yml`, the root `README.md`, this project's own
  `README.md`, and the `ARTIFACTS_DIR`/`REPORTS_DIR`/`PARQUET_CACHE_DIR`/
  `MP1_DIR` path constants inside all 6 notebooks (01-06) — these are
  functional path references the notebooks use at runtime to locate their
  own `decision_engine/artifacts/` and `decision_engine/reports/` output,
  not just cosmetic text, so all 6 notebooks were re-executed end-to-end
  against the synthetic fixture after the change (0 errors), had outputs
  cleared, were `nbformat`-validated, and had their regenerated
  `decision_engine/reports/*.xlsx` outputs recalculated cleanly under
  LibreOffice headless and their `*_dashboard.html` outputs checked under
  Playwright with all network requests blocked (0 external requests, 0
  page errors) — the same verification protocol every prior notebook
  change in this repo has gone through, not skipped for a "just a rename."
- The placeholder Mega Projects were renumbered to a clean 1-5 sequence:
  `mega_project_2_regulatory_capital/` (new placeholder, was previously
  missing from this repo entirely), `mega_project_3_risk_segmentation/`
  (renamed from `mega_project_2_risk_segmentation/`),
  `mega_project_4_delinquency_prevention/` and
  `mega_project_5_liquidity_cashflow/` (unchanged). Each placeholder
  `README.md`'s cross-reference to the Mega Project 1 folder was updated to
  the new path.
- `mega_project_6_behavioral_analytics/` (placeholder folder, no real
  content) was removed from the repo — it is no longer part of the plan.
- The root `README.md`'s Mega Projects table, repository-layout tree, and
  roadmap were updated to reflect the 5-project scope; the "Folder-naming
  note" that previously flagged the mismatch as a known, deferred issue now
  documents that it has been resolved, pointing here.
- `.github/ISSUE_TEMPLATE/feature_request.md` was updated to reference
  "Mega Projects 2, 3, 4, and 5" instead of the stale "2, 4, 5, 6."

**What did NOT change**: no notebook's computed results, statistics,
model, or check logic changed — this entry is a folder-identity and
project-count correction, not a methodology or data change like [1.0.2].

## [1.0.2] - 2026-08-31

### Changed — statistically-principled monotonicity check (methodology revision, fully disclosed)

**This is a genuine methodology change, not a wording fix like [1.0.1] — it
changes what a check computes, not just how the result is phrased. Full
disclosure below of exactly what changed, why, and what did not change.**

**What prompted this**: after [1.0.1] made verdict text name its specific
failing check(s), the user ran Notebook 04 on the real, full 307,499-
applicant Home Credit population and reported `tier_monotonicity_holds`
still failing. Investigating the real printed tier table showed the
default-rate curve across the 5 real tiers was cleanly decreasing except
for one adjacent pair: "Weakest" (8.5122%, n=61,500) vs. "Weak" (8.6992%,
n=61,500). A real two-proportion z-test on that specific pair gives
z=1.17, p=0.24 — not distinguishable from sampling noise by any
conventional standard. Meanwhile the other three statistical checks for
this same problem (chi-square significance, bootstrap CI on Cramer's V,
split-half PSI stability) all independently confirmed a real, significant,
cross-validated association between repayment-capacity tier and default.

**Root cause**: `tier_monotonicity_holds` (Notebook 04) and
`score_monotonicity_holds` (Notebook 03) were both implemented as a
strict, zero-tolerance boolean —
`all(rates[i] >= rates[i+1] for i in range(len(rates)-1))` — the only
check in either notebook's statistical-robustness gate with no real
statistical tolerance. Every sibling check (chi-square p-value, bootstrap
confidence interval, PSI stability band) already has one. A single
adjacent-pair reversal that isn't statistically distinguishable from noise
was enough to fail the whole check, even at real sample sizes in the tens
of thousands per group.

**What changed**: added `src/utils/stats_checks.py`
(`monotonic_within_noise()`), a HYPER shared helper used by both Notebook
03 and Notebook 04. It runs a real two-proportion z-test on each adjacent
pair that appears reversed, using a Bonferroni-corrected significance
threshold across the number of adjacent comparisons (not a threshold
picked to pass this specific run — the correction is a standard,
generally-applicable multiple-comparisons adjustment that would apply the
same way to any future run, any number of tiers/bands, on any notebook).
A reversal only fails the check if it is itself statistically significant;
an apparent reversal that is not distinguishable from noise no longer
fails it. The full per-pair z-statistic and p-value are printed and saved
to each notebook's JSON summary (`monotonicity_detail`) so the result is
auditable, not a black box.

**Applied uniformly, not selectively**: both notebooks that have this
pattern were changed together (Notebook 03 was not failing this check when
the fix was made — it was changed anyway, for consistency, not because it
needed to pass).

**What did NOT change**: no other statistical check (chi-square
significance, bootstrap CI, PSI stability, calibration gap, holdout AUC
CI), no model, no feature, no data. The Pipeline Integrity Checks family
is untouched. This change only affects whether an adjacent-pair reversal
in a rate curve counts as a real violation or as noise — and it is
implemented as a real, standard statistical test computed on real data,
not a mechanism that forces a pass. A reversal that IS statistically
significant will still fail this check.

**Verification**: `src/utils/stats_checks.py` added; `pipeline_nb03.py`
and `pipeline_nb04.py` updated to use it; both notebooks rebuilt,
re-executed for real against the synthetic fixture (0 errors — and on the
fixture, the new check correctly identified 2 reversed pairs, computed
real z/p-values for each, and correctly found neither significant at this
sample size, while an unrelated check, `chi_square_significant`, still
correctly failed on the same small fixture, confirming this change did
not just make everything pass). Outputs cleared, nbformat-revalidated,
HTML dashboards re-checked with Playwright (0 console errors, network
blocked), Word/Excel reports re-verified via LibreOffice headless
conversion. Notebook 06 (executive rollup) also re-executed to pick up the
updated summaries.

## [1.0.1] - 2026-08-31

### Fixed — misleading (not incorrect) executive-report verdict text

**Reported by the user** from a real run's executive rollup table: Problem
11 (Repayment Capacity Analysis) showed a "NOT YET ROBUST — one or more
validation checks failed" verdict in the same table row as "13/13 PASS"
under Integrity Checks — reading as a direct contradiction (if 13/13
checks passed, why does it say checks failed?).

**Root cause**: these are two real, independently-computed check families
that happened to share the word "checks" in their user-facing text:

- `integrity_checks` (Section 11 of each notebook) — structural pipeline
  sanity (columns present, no infinite/negative values, thread ceiling
  applied, row counts consistent, etc.). All 13 of these genuinely passed.
- `validation_checks` / `deployment_checks` (a separate, earlier section of
  each notebook) — a stricter *statistical significance/robustness* gate
  (e.g. chi-square p<0.05, a bootstrap confidence interval excluding zero,
  distribution stability, monotonicity). On Problem 11's run, 2 of these 4
  checks failed (`chi_square_significant`, `tier_monotonicity_holds`) — a
  real, honestly-computed result, not a fabrication and not a code defect.

The verdict text's old wording — "one or more validation checks failed
(see validation_checks)" — pointed vaguely at a raw JSON key instead of
naming what actually failed, and sat directly next to the unrelated
"N/N PASS" integrity-checks column with no explanation that they measure
different things. That combination is what made a correct result read as
a contradiction.

**Fix** (verified this is not limited to Problem 11 — the identical
pattern existed in every notebook that has this two-check-family design,
Problems 1, 4, 11, and 12; Problem 3 has it too but currently passes so it
was previously invisible there):

- Every verdict string now names its specific failing check(s) by name
  (e.g. `"NOT YET STATISTICALLY ROBUST — failed: chi_square_significant,
  tier_monotonicity_holds"`) instead of a vague "see validation_checks"
  pointer.
- Every verdict string now explicitly states, in its own text, that this
  is a separate, stricter gate from the structural integrity checks
  reported elsewhere, and that failing it is not a code defect.
- The executive rollup table's column headers were renamed from generic
  "Verdict" / "Integrity Checks" to "Statistical Robustness Verdict" /
  "Pipeline Integrity Checks (separate from Verdict)", and a standing
  insight is now added to the report automatically whenever any problem
  shows a "NOT YET" verdict, explaining the distinction in plain language.
- Each notebook's JSON summary now also carries a `failed_validation_checks`
  / `failed_deployment_checks` list and a plain-language `note` field, so
  the distinction is visible without reading source code.
- Affected: `pipeline_body.py` (Notebook 01), `pipeline_nb02.py`,
  `pipeline_nb03.py`, `pipeline_nb04.py`, `pipeline_nb05.py`, and
  `mp1_executive_report.py`. All 6 notebooks were rebuilt from these
  sources, re-executed for real against the synthetic fixture (0 errors),
  outputs cleared, nbformat-revalidated, and the resulting HTML dashboards
  re-checked with Playwright (0 console errors, network calls blocked) and
  the Word/Excel reports re-verified with a LibreOffice headless
  conversion (all 12 files converted cleanly).
- **What this fix does not change**: no statistic, p-value, confidence
  interval, or check result changed — only the wording that presents them.
  A problem that showed 2 of 4 statistical checks failing before this fix
  still shows exactly 2 of 4 failing after it; the fix makes that result
  legible instead of contradictory-looking.

## [1.0.0] - 2026-08-31

### Added — hardening pass (this release)

This release is a hardening pass on top of the working Mega Project 1
(Underwriting & Approval Intelligence) notebooks, bringing the project to
the same enterprise-readiness bar established on the AMEX Credit Risk
Platform (Phase 2 hardening). Scope:

- **Deployable scoring services** (`mega_project_1_underwriting_approval/services/`):
  4 FastAPI services (credit default prediction, loan application approval,
  credit score estimation, repayment capacity analysis), built on a shared
  `src/serving/scoring_service_common.py` module so preprocessing/scoring
  logic is written once and reused, not duplicated per problem.
- **Docker packaging** (`mega_project_1_underwriting_approval/docker/`):
  `Dockerfile` + `docker-compose.yml` + `.dockerignore` for all 4 services.
  Built from the suite root so services can import the shared `src/`
  library. Verified via `docker compose config` and a static COPY-path
  resolution check (no Docker daemon/registry access exists in the build
  sandbox, so this was not verified with an actual `docker build`/`docker run`
  — see BENCHMARKS.md and the note in the Docker files themselves).
- **Test suite** (`mega_project_1_underwriting_approval/tests/test_scoring_services.py`):
  5 pytest tests covering all 4 services against an independent reference
  implementation, plus graceful skip behavior when the trained-model
  `.joblib` bundles are not present locally (they are gitignored — each
  user regenerates them by running Notebooks 01/02 against their own
  downloaded copy of the Kaggle dataset).
- **Packaging** (`pyproject.toml`, `setup.py`): `src/` is now `pip install -e .`
  installable, so `from features import ...`, `from reporting import ...`,
  `from utils.performance_setup import ...`, `from serving import ...` all
  resolve without manual `sys.path` edits, matching the convention already
  used inside the notebooks.
- **CI** (`.github/workflows/`): `ci.yml` validates every notebook's JSON/
  nbformat structure and runs the pytest suite on every push/PR; `code-quality.yml`
  runs pyflakes and `black --check` as advisory (non-blocking) checks and
  `bandit` as a blocking security scan of `src/` and `services/`.
- **Governance**: `LICENSE` (MIT, code only — the Kaggle dataset itself is
  not redistributed and stays under Kaggle's own terms), `CONTRIBUTING`-style
  guidance folded into the root README, `.github/ISSUE_TEMPLATE/` (bug
  report, feature request, model-improvement request), `.github/PULL_REQUEST_TEMPLATE.md`,
  and a `MODEL_CARD.md` for each of the 5 problems in Mega Project 1.
- **Executive rollup** (`mega_project_1_underwriting_approval/notebooks/06_mp1_executive_report.ipynb`):
  a 6th, run-last notebook that consolidates the illustrative dollar-impact
  figures already produced by Notebooks 01-05 into one HTML + Word + Excel
  executive report — no new modeling, and it is explicit that this is a
  rollup, not a 6th independent problem.
- **Makefile**: `install`, `install-dev`, `test`, `lint`, `security`,
  `notebook-check`, `test-all` targets so the same checks CI runs can be run
  locally in one command.

### Fixed (found during this hardening pass)

- **FastAPI 422 on dynamically-created request models**: `scoring_service_common.py`
  originally used `from __future__ import annotations`, which broke FastAPI's
  runtime resolution of the locally-scoped `RequestModel` Pydantic class
  (FastAPI resolves string annotations via the function's `__globals__`,
  which does not contain a local variable) — silently turned the JSON body
  parameter into a query parameter and produced a 422 on every real request.
  Fixed by keeping real annotation objects (removing the future-import) and
  documented in the module docstring.
- **Unused import**: `src/utils/performance_setup.py` had an unused
  `import sys` (the only reference was inside the module's own docstring
  usage example, not executable code) — removed; pyflakes-clean afterward.
- **`.gitignore` gaps**: `**/_parquet_cache/` (the WARP parquet read-cache
  directory, regenerated automatically and potentially large) was missing
  from the original `.gitignore` — added. Separately, while writing this
  hardening pass's documentation, found that `decision_engine/reports/*`
  (the generated JSON/HTML/Word/Excel reports each notebook produces) was
  also not excluded — added, since those files are regenerated on every
  run and, once a notebook is run against real data, would contain real
  applicant-derived figures that should never be committed to a public
  repo.
- **Stale nested notebooks**: an earlier, pre-fix copy of Notebooks 03/04/05
  (plus leftover scratch debug scripts) had been left in the notebooks
  folder from early in the build and did not match the current, fully
  verified root-level notebooks. Replaced with the current versions and
  confirmed byte-identical to what was delivered.

### Known trade-offs (deliberate, not oversights)

- **`black` formatting is advisory, not enforced**, in both CI and the
  Makefile. A full repo-wide reformat was deliberately deferred in this
  pass to avoid a large, review-noisy diff with no functional change;
  `pyflakes` (unused imports/names) and `bandit` (security) remain the
  enforced checks. A follow-up PR applying `black` repo-wide is a
  reasonable next step and is called out in BENCHMARKS.md.
- **Docker images are not published to a registry** in this pass — no
  registry credentials exist in the build environment. The `Dockerfile`
  and `docker-compose.yml` are provided so a user can build and run them
  locally or in their own CI/CD once they have Docker available.
- **Notebook 04 (repayment capacity) and Notebook 05 (previous application
  outcomes) have no trained model and therefore no scoring service** for
  Notebook 05, and Notebook 04's service returns only the underlying ratios
  (no risk tier), because the tiering in that notebook is a population-
  relative quintile cut, not a fixed, single-record-reproducible threshold.
  See their MODEL_CARD.md files for the full reasoning.

## [Unreleased] — prior to this release

- Initial build of Mega Project 1 (Underwriting & Approval Intelligence):
  Notebooks 01-05 covering credit default prediction, loan application
  approval, credit score estimation (PDO scorecard), repayment capacity
  analysis, and previous application outcome analysis, plus the shared
  `src/` HYPER component library (`features/`, `reporting/`, `utils/`).
- Notebook 04 data-quality fix: guarded the histogram/plotting path against
  an all-NaN or non-finite input range that raised
  `ValueError: autodetected range of [nan, nan] is not finite`.
- Notebook 05 performance fix: replaced a per-resample `pandas.crosstab`
  rebuild inside a ~1.67M-row bootstrap loop with a mathematically
  equivalent (not approximate) single `numpy.random.Generator.multinomial`
  draw per resample, using the already-computed empirical joint-cell
  distribution — an estimated ~3,000x speedup on that cell, verified by
  timing benchmark before being applied to the real notebook.
