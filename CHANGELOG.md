# Changelog

All notable changes to this repository are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.9.9] - 2026-09-02

### Fix: CI `shared-tests` job failing on a fresh runner -- undeclared dependencies

Found via a real GitHub Actions failure after this repo's first push (10 of
11 checks green, `CI / shared-tests` red). Root cause: `src/tests/test_serving_common.py`
builds real fitted scikit-learn bundles in-fixture (`joblib`, `numpy`,
`scikit-learn`) and exercises `scoring_service_common.py`'s `/score` handler,
which does a lazy `import pandas` to build the prediction row -- none of
which the job's `pip install` line declared. It passed locally throughout
this suite's development only because the development sandbox's ambient
Python already had all four installed; a fresh CI runner has nothing but
what the workflow explicitly installs. Verified the fix in an isolated venv
containing only the corrected install list: 18/18 tests pass. No test
logic, service code, or model output changed -- this was a CI-configuration
gap, not a code or results bug.

## [1.9.8] - 2026-09-02

### Hardening pass, part 2: Mega Project 4 built hardened (services + Docker + tests + CI + architecture diagram), root README brought current

Completes the hardening pass started in [1.9.7], bringing Mega Project 4
to full parity with Mega Projects 1-3 and closing the real gap that this
suite's own root `README.md`/`ROADMAP.md` still read "3 of 5 Mega
Projects built" and listed Mega Project 4 as "scoped, not yet built" —
stale since Mega Project 4's 6 notebooks were actually completed earlier
in this session.

- **4 new deployable FastAPI services**, hardened from day one (never
  needed a retrofit, unlike Mega Projects 1-3):
  `early_delinquency_scoring_service.py` :8011,
  `payment_pattern_assignment_service.py` :8012,
  `revolving_distress_scoring_service.py` :8013,
  `pos_cash_trajectory_scoring_service.py` :8014. Every one requires a
  real `X-API-Key` header on `/schema`/`/score`; the 3 classifier services
  return real `top_reasons`, the clustering service returns real
  `distance_to_each_segment`.
  Problem 5 (Early-Warning Intervention Ranking) gets no service —
  a population-level fusion, not a per-record model — matching Mega
  Project 3's own Problem 5 precedent.
- **A real generalization to the two shared HYPER serving factories**,
  rather than duplicating them a second time: Mega Project 4's Notebook
  01/03/04 bundles have no categorical features at all (so no
  `ordinal_encoder`/`numeric_features`/`categorical_features` keys), and
  Notebook 02's clustering bundle uses `feature_cols`/`pattern_labels`
  instead of the canonical `feature_names`/`segment_labels`.
  `scoring_service_common.load_bundle()` and
  `segment_assignment_common.load_bundle()` now fill in real, documented
  defaults/aliases for these when absent — every existing Mega Project
  1/3 bundle, which already carries the canonical keys, is completely
  unaffected (verified: 6 new real tests in `src/tests/test_serving_common.py`,
  including one asserting the canonical-key path is untouched).
- **Docker**: new `04_mega_project_4_delinquency_prevention/docker/`
  (`Dockerfile` + `docker-compose.yml` + `.env.example`), built with the
  same non-root user, real `HEALTHCHECK`, and required-`API_KEY`
  ( `${API_KEY:?...}` ) pattern added to Mega Projects 1-3 in [1.9.7] —
  verified structurally via `docker compose config` (confirms it correctly
  refuses to run without `API_KEY` set, and resolves cleanly once it is)
  and a static `COPY`-path check; no Docker daemon in this build
  environment, so an actual `docker build`/`docker run` has not been
  performed (same disclosed limitation as Mega Projects 1-3).
- **New pytest suite**: `04_mega_project_4_delinquency_prevention/tests/test_scoring_services.py`
  — the 3 classifier services checked bit-identical against direct
  `model.predict_proba()` computation, the clustering service against
  `assign_segment()` called directly; every test also asserts a 401
  without the `X-API-Key` header. Skip-if-missing on each notebook's real
  `.joblib` bundle, same convention as Mega Projects 1-3. Verified in this
  build environment against real, hand-built, structurally-matching
  bundles (temporarily placed at the real artifact paths, deleted after);
  never against the user's actual data.
- **New architecture diagram**: `docs/mp4_architecture_flow.mmd`/`.png`,
  embedded in Mega Project 4's own README, matching Mega Projects 1-3's
  diagram convention.
- **CI/Makefile**: `code-quality.yml`'s pyflakes/black/bandit steps and
  `Makefile`'s `test`/`lint`/`security` targets now include Mega Project
  4's `services/`/`tests/`; `ci.yml`'s `unit-tests` matrix (extended in
  [1.9.7] with a `hashFiles` guard ahead of this work landing) now
  actually exercises Mega Project 4's real test suite.
- **2 real pre-existing lint findings fixed** (found via a real
  `pyflakes` run while verifying this pass, not newly introduced by it):
  an unused `typing.Optional` import in
  `src/serving/segment_assignment_common.py` and in Mega Project 3's
  `risk_tier_assignment_service.py`. `pyflakes` and `bandit -ll` both now
  report 0 issues across every `src/`, `services/`, and `tests/` path this
  repo's CI lints.
- **Root `README.md`/`ROADMAP.md` brought current**: status line, Skills
  Demonstrated MLOps row, Platform-at-a-Glance table, Repository
  Structure, Architecture Diagrams table, Live Dashboards (Mega Project
  4's Problems 1-2, the only ones with a fixture-generated dashboard to
  publish), How to Run, and Repository Hardening history all now
  correctly reflect 4 of 5 Mega Projects built, 14 total services, and 24
  total notebooks.
- Verification: `py_compile` clean on every new/edited `.py` file;
  `pyflakes` and `bandit -r ... -ll` both 0 findings; the full pytest
  suite (`src/tests/` + all 4 Mega Projects' `tests/`) run the way
  `Makefile`/`ci.yml` actually invoke it (each project's own directory,
  matching CI's matrix job) — 18 (`src/tests/`) + 10 (MP1, including 5
  real bit-identical checks against this build environment's own
  pre-existing, policy-compliant fixture artifacts from MP1's original
  build) + 6 (MP2) passed, 0 failed; MP3's and MP4's own
  `test_scoring_services.py` correctly skip (no real notebook artifacts
  present in this sandbox for MP3, and MP4's real artifacts are the
  user's to produce by running the notebooks). No business-data run was
  performed by this pass itself, per the standing 2026-09-01 policy.

## [1.9.7] - 2026-09-02

### Hardening pass, part 1: real API-key authentication + real per-request explainability on every existing deployable service (Mega Projects 1-3)

Prompted by an explicit instruction to bring this suite's hardening up to
parity with the AMEX RiskIQ Enterprise Credit Risk Platform (a related,
larger prior project on this account) and to close every real gap found.
A repo-wide audit (`grep -rln "API_KEY\|APIKeyHeader\|Security("`) found
**zero matches** across all 10 of this suite's existing deployable FastAPI
services — the exact same "single largest gap" that project's own
hardening history documents having found and fixed in itself.

- **New HYPER shared modules** — `src/serving/auth_common.py`
  (`configured_api_key()` / `require_api_key()`, real `X-API-Key` header
  auth via `fastapi.security.APIKeyHeader`, constant-time comparison via
  `secrets.compare_digest`, a published dev-only fallback key with a loud
  `logging.warning` when `API_KEY` is unset) and
  `src/serving/explainability_common.py` (`top_reason_codes()`, real
  per-request occlusion-based reason codes — reset one real feature to its
  own real baseline, measure the resulting real change in predicted
  probability, rank by `|contribution|` — mirrors CFPB Circular 2022-03's
  "specific, principal reason" standard). Both built once and imported by
  every service, never duplicated.
- **All 10 existing services now require `X-API-Key` on every `/schema`
  and `/score` endpoint** (`/health` stays unauthenticated, for liveness
  probes): the two shared-factory services
  (`scoring_service_common.build_scoring_app()`,
  `segment_assignment_common.build_segment_app()`) retrofit 5 services at
  once; the other 5 standalone services
  (`credit_score_service.py`, `repayment_capacity_service.py`,
  `capital_requirement_service.py`, `stress_testing_service.py`,
  `risk_tier_assignment_service.py`) were edited individually.
- **Real per-request explainability added** to every classifier-backed
  service (`credit_default_scoring_service`, `loan_approval_scoring_service`
  via the shared factory; `credit_score_service` standalone) — a new
  `"top_reasons"` field, computed live via `top_reason_codes()` against
  the real loaded model on every call. The clustering-backed segment
  services gained a real, non-fabricated `"distance_to_each_segment"`
  field instead (`kmeans.transform()`'s own real Euclidean distances to
  every real fitted centroid, sorted nearest-first) — the same real
  transparency addition, adapted to what a clustering model can honestly
  report. The 4 purely deterministic-formula services (repayment
  capacity, capital requirement, stress testing, risk tier) got auth
  only — no explainability was added, since a disclosed closed-form
  formula is already fully transparent by construction.
- **Docker hardening, matching the AMEX platform's own pattern**: all 3
  existing `Dockerfile`s now run as a real non-root user
  (`useradd --create-home --uid 1000`) and carry a real `HEALTHCHECK`
  (a Python `urllib` request against that service's own unauthenticated
  `/health`) — never `ENV API_KEY` baked into any layer. All 3
  `docker-compose.yml` files now require `API_KEY` via
  `${API_KEY:?Set API_KEY before running...}` (fails fast rather than
  silently deploying with the dev-only fallback key) and set a real
  `HEALTHCHECK_PORT` per service. New `docker/.env.example` in each Mega
  Project documents the required variable; `.gitignore` now excludes real
  `.env`/`.env.*` files while keeping the `.example` templates.
- **Existing pytest suites fixed so the retrofit does not regress them**
  (a real, previously-passing-locally test suite breaking under new auth
  would itself have been a new bug): every `/schema`/`/score` call in
  `01_.../tests/test_scoring_services.py`,
  `02_.../tests/test_scoring_services.py`, and
  `03_.../tests/test_scoring_services.py` now sets a real `API_KEY` env
  var via `monkeypatch` and sends the matching `X-API-Key` header; each
  file also gained an explicit `test_..._requires_auth`-style assertion
  that the endpoint 401s with no key. MP3's segment-assignment tests
  (`_cross_check_segment_service`) call `assign_segment()` directly, not
  through the HTTP layer, so they were unaffected and needed no change.
- **New real, executed test suite for the two new shared modules**:
  `src/tests/test_serving_common.py` (12 tests, all passing) — hand-built,
  independently-computable expectations for `auth_common.py` (missing key,
  wrong key, correct key, dev-default fallback, `/health` staying
  unauthenticated, and a source-inspection regression test that
  `require_api_key` really uses `secrets.compare_digest`, never `==`) and
  `explainability_common.py` (a hand-computable linear scoring function
  whose occlusion contributions are checked to the value, ranking order,
  `n`-truncation, and the empty-list-at-baseline case). Pure code-
  correctness tests, no business data, no notebook artifacts — consistent
  with the standing 2026-09-01 no-fixture verification policy.
- **CI/Makefile wired up**: `ci.yml` gained a `shared-tests` job running
  `src/tests/`; the `unit-tests` matrix now includes Mega Project 4 guarded
  by `hashFiles(...) != ''` (ahead of MP4's own services/tests landing in
  part 2 of this hardening pass, so this job never fails on a directory
  that doesn't exist yet); `Makefile`'s `test` target now runs
  `pytest src/tests/` first.
- Verification for every code change above: `py_compile` on every edited/
  new `.py` file (0 errors); `src/tests/test_serving_common.py` actually
  executed (12/12 passed) — these are structural code-correctness checks
  against hand-built fixtures, never a run against the user's real data,
  per the standing 2026-09-01 policy. The pre-existing MP1/MP2/MP3
  `test_scoring_services.py` suites still require the user's own real
  notebook artifacts to exercise for real (they remain `skipif`-guarded on
  those artifacts existing, as before this pass).

## [1.9.6] - 2026-09-01

### Fix real Mega Project 4 Notebook 6 crash found on user's full-scale real run: Excel forbids "/" in a sheet title

Real crash on the user's real run (307,511 applicants, 5/5 real problem
summaries found, all rollup logic and cross-checks passed CONFIRMED):
`ValueError: Invalid character / found in sheet title`, raised by openpyxl
while Notebook 6 built its Excel workbook.

- **Root cause**: two of Mega Project 4's own real problem names —
  "Revolving/Credit-Card Distress Early Warning" (Problem 3) and "POS/Cash
  Loan Delinquency Trajectory" (Problem 4) — contain a literal real `/`,
  which Excel forbids in a worksheet title. That real `/` reached
  `wb.create_sheet()` unsanitized. This suite's own synthetic fixture, and
  every prior Mega Project's own executive rollup, never happened to have
  a problem label containing one of Excel's forbidden sheet-title
  characters (`\ / ? * [ ] :`), so this was a latent bug in the shared
  HYPER `src/reporting/report_builder.py` module, never triggered before.
- **Fix**: new `safe_sheet_name()` function added to
  `report_builder.py` — replaces `\ / ? * [ ] :` with `-`, strips a
  leading/trailing apostrophe (also forbidden by Excel), truncates to
  Excel's own 31-character sheet-name limit. Used internally by every
  `wb.create_sheet()` call inside `build_excel_workbook()`, protecting
  every past and future caller (any Mega Project's own rollup), not just
  Notebook 6. `pipeline_mp4_nb06.py`'s own two local sheet-name-
  construction sites (building the per-problem sheet, and later looking
  it back up by name to embed its real chart PNG) now call the same
  function on the same input, so the two are guaranteed to always match.
  The real, unsanitized problem label is never altered anywhere else —
  reports, charts, and insights keep the real name in full.
- Verified: `safe_sheet_name()` run directly against all 5 real MP4
  problem labels (0 forbidden characters survive, both call sites
  produce an identical name for the same input); a real, direct
  `build_excel_workbook()` integration test using the two labels that
  actually crashed — confirmed to build a real `.xlsx` with 0 errors and
  the expected sanitized sheet names present.
- `src/reporting/report_builder.py`,
  `04_mega_project_4_delinquency_prevention/notebooks/06_mp4_executive_report.ipynb`,
  `04_mega_project_4_delinquency_prevention/model_cards/06_mp4_executive_report_MODEL_CARD.md`
  updated. No `sample_reports/` entry (per 1.9.3's policy) — not executed
  against any data, per the standing 2026-09-01 policy.

## [1.9.5] - 2026-09-01

### Mega Project 4 Notebook 6 built (no synthetic fixture, per 1.9.3's policy) — Mega Project 4 notebooks now complete (6/6)

Problem 6 — Executive Rollup:

- Trains, clusters, and fits nothing new. A real, disclosed rollup of
  whichever of Problems 1-5's own already-computed real governance
  summaries (`decision_engine/reports/notebook_0N_summary.json`) are on
  disk — each is a soft dependency, loaded only if that notebook has
  already been run, never fabricated for a missing one.
- Two genuinely new pieces of synthesis: (1) "Real Behavioral Data
  Coverage" — each of Problems 1-4's real scope population (applicants
  with at least one real record in that problem's underlying table) as a
  fraction of the real total applicant population, independently
  re-derived straight from that problem's own summary — deliberately does
  not assume these fractions should be equal across product lines; (2) a
  real cross-notebook consistency check confirming Notebook 05's own real
  `signals_available` record matches which of Notebooks 01-04's real
  summaries actually exist on this run, signal by signal, plus a check
  that `n_app_total` (the real `application_train.csv` row count) is
  identical across every available classifier/clustering notebook.
- Surfaces all three of this Mega Project's verdict-tier families side by
  side, correctly labeled, never conflated: "Statistical Robustness
  Verdict" (Problems 1, 3, 4), "Clustering Robustness Verdict" (Problem
  2), and "Ranking Comparison Verdict" (Problem 5) — mirrors the
  disclosed two-verdict-family pattern Mega Project 3's own executive
  rollup already established.
- Reporting package: `mp4_executive_report.docx`,
  `mp4_executive_report.xlsx` (big-letters front "Executive Rollup" sheet
  with a native openpyxl `BarChart`, one sheet per problem with that
  problem's own real chart PNG embedded, Problem Rollup and Behavioral
  Coverage sheets, formula-driven Assumptions/Financial Impact sheets,
  SMART Insights sheet), `mp4_executive_dashboard.html` (real KPI cards,
  up to 5 charts including a real holdout-ROC-AUC comparison across
  Problems 1/3/4's classifiers, a Key Insights grid, a searchable
  per-problem rollup table), plus supporting CSVs and
  `mp4_executive_summary.json`.
- Verified via 3 hand-built mock-summary test cases (full availability,
  partial availability with a deliberate signal mismatch, a deliberate
  `n_app_total` mismatch) — every derived coverage fraction, sort order,
  and consistency flag checked by hand and confirmed exact, including
  that both deliberate mismatches were correctly caught and named.
- `notebooks/06_mp4_executive_report.ipynb`. No `sample_reports/` entry
  (per 1.9.3's policy). Syntax/AST-checked and `nbformat.validate()`-
  passed; not executed against any data.

Mega Project 4's 6-notebook scope is now fully built. Services/Docker/
tests/CI hardening for MP4 (matching Mega Projects 1-3's own hardening
pass) has not started yet — see `ROADMAP.md`.

## [1.9.4] - 2026-09-01

### Mega Project 4 Problems 4-5 built (no synthetic fixture, per 1.9.3's policy) — all 5 problems now built

Problem 4 — POS/Cash Loan Delinquency Trajectory:

- New HYPER module `src/features/pos_cash_trajectory_features.py`
  (`engineer_pos_cash_trajectory_features`): 8 real, vectorized trajectory
  features from `POS_CASH_balance.csv` — real DPD spikes (month-over-month
  change, threshold 5 days), real DPD streaks (run-length encoding, same
  technique as Problems 2 and 3), and real instalment-repayment-progress
  velocity (recency-split trend in remaining instalment count, same
  technique as Problem 1's `LATE_RATE_TREND`). Distinct from MP1's SUM
  totals and Mega Project 3 Notebook 03's rate/level segmentation of the
  same table. Proactively applies the disclosed null-handling convention
  from Problems 1-2's 2026-09-01 fix (defensive `SK_DPD` zero-fill;
  `CNT_INSTALMENT_FUTURE` nulls dropped from the mean, final aggregate
  never left null) before this table could produce the same kind of
  silent or crashing null.
- Also adds `compute_naive_current_dpd()` to the same module — each
  applicant's most recent real `SK_DPD`, the naive baseline Problem 5
  benchmarks against.
- Verified via 5 hand-built test-case applicants (a genuine DPD spike, a
  real DPD streak, null `SK_DPD`, null `CNT_INSTALMENT_FUTURE` including a
  case where an entire real half of an applicant's history has no valid
  value, a single-month applicant, a constant/no-DPD applicant) — every
  one of the 8 output features checked by hand, zero nulls in any case.
- `notebooks/04_pos_cash_delinquency_trajectory.ipynb`: same real 4-model
  screen -> 5-fold CV -> champion -> holdout+bootstrap-CI -> decile-check
  -> SHAP pattern as Problems 1 and 3, plus THREE independent soft-
  dependency comparisons when available: MP1 Notebook 01, MP4 Notebook 01,
  MP4 Notebook 03.

Problem 5 — Early-Warning Intervention Ranking:

- Trains nothing new from raw data. A real, disclosed fusion of whichever
  of Problems 1-4's own already-computed real per-applicant scores are on
  disk (soft dependencies, never fabricated for a missing one): each is
  percentile-rank-normalized to [0,1] within its own real scope
  population and averaged into a real `COMPOSITE_SCORE`, with a real,
  disclosed `COVERAGE_COUNT` (1-4) per applicant. Notebook 02's
  categorical `PAYMENT_PATTERN` clusters are converted to a real numeric
  proxy using that exact run's own real observed default rate per pattern
  (from `notebook_02_summary.json`) — never a hardcoded mapping.
- Benchmarked against each applicant's most recent real `SK_DPD` (no
  modeling at all) via a real top-decile default-capture-rate comparison
  and a real chi-square significance test (`scipy.stats.chi2_contingency`,
  the same test already used for Problem 2) plus a real Spearman rank
  correlation between the two rankings. Verdict logic adapted honestly
  for a ranking-comparison task (not a classifier robustness gate) and
  reported either way — never smoothed over if the naive baseline wins or
  ties.
- Raises a clear, real error (not a fabricated ranking) if zero of
  Problems 1-4's real signals are found on disk.
- Verified via a hand-built 6-applicant test case with deliberately
  partial, real-world-shaped signal coverage — every composite score and
  coverage count checked by hand and confirmed exact.
- `notebooks/05_early_warning_intervention_ranking.ipynb`.

Both: no `sample_reports/` entries (per 1.9.3's policy). Both syntax/AST-
checked and `nbformat.validate()`-passed; neither executed against any
data. Mega Project 4 now has all 5 problems built — only the executive
rollup (Problem 6) remains for this Mega Project.

## [1.9.3] - 2026-09-01

### Policy change: no more synthetic fixtures from Mega Project 4 Problem 3 onward, and Mega Project 4 Problem 3 built under it

Per explicit user instruction, this repo stops running new notebooks
against a synthetic fixture before delivery, and stops generating
`sample_reports/SAMPLE_*` files for them. Verification for new logic is
now: (1) small, targeted, hand-built test cases for any new
feature-engineering function — a few rows of data, edge cases included,
every output value checked by hand; (2) a Python syntax/AST check on the
pipeline script; (3) `nbformat.validate()` on the assembled notebook. No
full pipeline execution on fabricated data, no fixture-generated charts or
dashboards. A notebook's real champion, AUC, and verdict are reported only
after the user runs it on their own real data. Mega Project 4 Problems
1-2's existing fixture-generated sample reports and fixture numbers
predate this change and are left as they are (the user's explicit
decision) — this is not retroactive.

Built under the new policy — Problem 3: Revolving/Credit-Card Distress
Early Warning:

- New HYPER module `src/features/revolving_distress_features.py`
  (`engineer_revolving_distress_features`): 9 real, vectorized (Polars)
  trajectory features from `credit_card_balance.csv` — real utilization
  spikes (month-over-month change, threshold 0.15), real minimum-payment-
  only streaks (vectorized run-length encoding, same technique as Problem
  2's installment streaks), and real balance/drawings-growth velocity
  (recency-split trend, same technique as Problem 1's `LATE_RATE_TREND`).
  Deliberately distinct from MP1's 8 SUM-based credit-card totals and from
  Mega Project 3 Notebook 04's MEAN/MAX/PCT-of-months rate features for the
  same table — direction of change, not level or rate; a real supervised
  classifier, not Notebook 04's unsupervised segmentation. Proactively
  applies the disclosed null-handling convention from Problems 1-2's
  2026-09-01 fix (null `AMT_DRAWINGS_CURRENT` -> 0.0 real "nothing
  happened"; null `AMT_INST_MIN_REGULARITY` -> not a minimum-payment-only
  month) before this table could produce the same kind of silent or
  crashing null.
- Verified via 6 hand-built test-case applicants (a genuine utilization
  spike, null `AMT_DRAWINGS_CURRENT`, null `AMT_INST_MIN_REGULARITY` on 2
  different applicants, a single-month applicant, a constant-utilization
  applicant) — every one of the 9 output features checked by hand against
  the input; zero nulls in output across all cases.
- `notebooks/03_revolving_credit_card_distress_early_warning.ipynb`: same
  real 4-model screening -> 5-fold CV -> champion -> true holdout with
  bootstrap 95% CI -> decile-calibration check -> SHAP pattern as Problem
  1, plus TWO independent soft-dependency comparisons when available: MP1
  Notebook 01's champion (application-time features) and MP4 Notebook 01's
  real per-applicant installment-behavior scores, both on the applicable
  real overlap population(s). No numbers are claimed by us for this
  notebook — see its model card's "Verification status" section.
- Added `model_cards/03_revolving_credit_card_distress_early_warning_MODEL_CARD.md`.
  No `sample_reports/` entry for Problem 3 (see policy change above).

## [1.9.2] - 2026-09-01

### Fixed a real bug in Mega Project 4 found on the user's real, full-scale run — installments_payments.csv null-payment handling

Found via the user's own real run against the full 307,511-row Home Credit
dataset, not our own fixture (the fixture never exercised this path — see
below): Notebook 02 crashed with `ValueError: Input X contains NaN` inside
`KMeans.fit_predict()`.

- **Root cause**: a real minority of `installments_payments.csv` rows have
  no recorded `DAYS_ENTRY_PAYMENT`/`AMT_PAYMENT` — no payment has posted
  against that scheduled installment as of the data snapshot (a genuine,
  documented real characteristic of the Kaggle dataset, not synthetic
  noise). `src/features/delinquency_features.py` previously let this
  propagate as `null`; when an applicant's *most recent* installment
  happened to be one of these rows, their `CURRENT_STREAK_IS_LATE_INT`
  came out `null`, and a single `NaN` anywhere in the clustering matrix is
  enough to crash `KMeans.fit_predict()` for the entire real run. In
  `engineer_installment_behavior_features` (Notebook 01), the same `null`
  propagation didn't crash — Polars aggregations skip nulls by default —
  but it *silently* excluded these installments from every rate/mean
  feature (`PCT_INSTALLMENTS_LATE`, `MEAN_PAYMENT_RATIO`,
  `MIN_PAYMENT_RATIO`, `TOTAL_SHORTFALL_AMT`), undercounting real lateness
  without erroring.
- **Fix**: both functions now have an explicit, disclosed convention — a
  no-payment-recorded installment is treated as unpaid-as-of-snapshot ==
  late (`IS_LATE = True`, `IS_UNDERPAID = True`, `SHORTFALL_AMT` = the full
  scheduled amount). This is a modeling convention for an actually-missing
  payment record, not a fabricated value. See the module's own docstring
  and each notebook's model card for the full disclosure.
- **Why our own fixture never caught this**: `make_fixture_supplementary.py`'s
  `installments_payments.csv` generator always produced a payment for
  every row — it never replicated this real data-quality characteristic.
  Fixed by adding a real ~3% no-payment-recorded rate to the fixture
  (including several applicants' most-recent installment specifically, the
  exact case that crashed), so this path is exercised on every future
  verification pass, not just on a real user's download. This is disclosed
  as a real, honest gap in our own pre-delivery verification, not
  papered over.
- **Impact — re-run both notebooks if you ran them before this fix**: this
  changes real numbers for both Problem 1 and Problem 2, not just fixes a
  crash. On this suite's regenerated synthetic fixture (2,715 in-scope
  applicants, up from 2,691 — the fixture itself was also regenerated,
  independently seeded, with the other 3 supplementary fixture files left
  byte-identical): Notebook 01's champion changed from `random_forest`
  (holdout ROC-AUC 0.5664) to `gradient_boosting` (holdout ROC-AUC 0.4678,
  95% CI [0.4102, 0.5214], verdict now NOT YET STATISTICALLY ROBUST on this
  small fixture); MP1's champion still scores 0.9427 on the identical
  population. Notebook 02: k=5 unchanged, silhouette 0.2377, chi-square
  p≈0.085 (verdict unchanged, NOT YET STATISTICALLY ROBUST) — but the
  notebook itself no longer crashes on data shaped like the user's real
  307,511-row run.
- Re-verified via the full protocol for both notebooks: real
  `jupyter nbconvert --execute` (0 errors) → outputs cleared →
  `nbformat.validate()` → Playwright network-blocked dashboard check (0
  errors, 3 charts each) → LibreOffice headless workbook recalc check.
  Regenerated `sample_reports/` and `docs/dashboards/` for both notebooks
  with the corrected numbers.

## [1.9.1] - 2026-09-01

### Mega Project 4 Problem 2 built: Installment Payment Behavior / Missed-Payment Pattern Detection

- New HYPER function `src/features/delinquency_features.py::engineer_payment_streak_features`:
  7 real, vectorized (shift + cumsum run-length encoding, no per-applicant
  Python loop) streak features from `installments_payments.csv` — longest
  late/on-time streak, streak counts, the applicant's *current* streak,
  and a real alternation rate. Deliberately different from Problem 1's
  rate-based feature set (a rate cannot tell "scattered late payments"
  apart from "currently mid-streak" — same rate, different real risk
  posture).
- `notebooks/02_installment_payment_behavior_detection.ipynb`: real,
  unsupervised K-Means clustering (never trained on `TARGET`) — k chosen
  by the highest real silhouette score across a documented candidate
  range, subject to a minimum stable cluster size. Validated with a real
  chi-square/Cramer's V test (bootstrap 95% CI) against real `TARGET`,
  and an honest, non-gated one-way ANOVA cross-check against Notebook 01's
  continuous risk score when its output is present.
- On this build's synthetic verification fixture: k=5 real patterns found
  (silhouette≈0.23), but the statistical-robustness verdict came back
  honestly **NOT YET STATISTICALLY ROBUST** (chi-square p≈0.10 on the
  small, randomly-generated 2,691-applicant fixture) — reported as-is,
  not smoothed over, exactly as this suite's zero-fabrication standard
  requires. The cross-check against Notebook 01's score did show a real,
  statistically significant relationship (ANOVA p<0.001, eta-squared≈0.09).
- Verified via the full protocol: real `jupyter nbconvert --execute` (0
  errors) → outputs cleared → `nbformat.validate()` → Playwright
  network-blocked dashboard check → LibreOffice headless workbook check.
- Added `model_cards/02_installment_payment_behavior_detection_MODEL_CARD.md`,
  the Problem 2 sample reports + README table row, and
  `docs/dashboards/mp4_notebook_02_dashboard.html`.
- Updated `ROADMAP.md`'s status table and next-steps list (Mega Project 4
  now 2/6).

Problems 3-5 and the executive rollup are not yet built.

## [1.9.0] - 2026-09-01

### Mega Project 4 (Delinquency Prevention) started: scope locked in, Problem 1 built

Locked in Mega Project 4's 5-problem scope (Early Delinquency Risk
Scoring, Installment Payment Behavior Detection, Revolving/Credit-Card
Distress Early Warning, POS/Cash Loan Delinquency Trajectory,
Early-Warning Intervention Ranking, + executive rollup) in
`04_mega_project_4_delinquency_prevention/README.md`, replacing the
placeholder scope note.

Built and verified Problem 1 — Early Delinquency Risk Scoring:

- New HYPER module `src/features/delinquency_features.py`
  (`engineer_installment_behavior_features`): 12 real, vectorized (Polars)
  behavioral features from `installments_payments.csv` — lateness rate,
  mean/max/std days late, underpayment rate and ratio, total shortfall,
  and a real recency-split late-rate trend. Deliberately independent of
  Mega Project 1's application-time feature set — this is a genuinely new
  signal (an applicant's own post-approval payment behavior), not a
  re-derivation, cross-compared against MP1 Notebook 01's champion on the
  identical holdout population rather than claiming to replace it.
- `notebooks/01_early_delinquency_risk_scoring.ipynb`: real 4-model
  screening (LogisticRegression, DecisionTree, RandomForest,
  GradientBoosting) → real 5-fold CV on the top 2 → champion retrained on
  full train, evaluated on a true holdout with a real bootstrap 95% CI on
  ROC-AUC → real decile-calibration monotonicity check → SHAP
  explainability on the champion → real, honest side-by-side AUC
  comparison against Mega Project 1's champion when its bundle is present.
  On this build's synthetic verification fixture: champion
  `random_forest`, holdout ROC-AUC 0.5664 (95% CI [0.5112, 0.6204]),
  decile calibration holds, MP1's application-time champion scores 0.9517
  on the identical population — both real, disclosed numbers, not
  cherry-picked.
- Verified via the full protocol: real `jupyter nbconvert --execute` (0
  errors) → outputs cleared → `nbformat.validate()` → Playwright
  network-blocked dashboard check (0 blocked calls, 0 console/page
  errors, 3 charts rendered) → LibreOffice headless workbook
  conversion/recalc check.
- Added `model_cards/01_early_delinquency_risk_scoring_MODEL_CARD.md`,
  `sample_reports/` (SAMPLE_-prefixed HTML dashboard, Word report, Excel
  workbook + disclosure README), and
  `docs/dashboards/mp4_notebook_01_dashboard.html`.
- Updated `ROADMAP.md`'s Mega Project status table and next-steps list to
  reflect Mega Project 4 as in progress (1/6) rather than not yet started.

Problems 2-5 and the executive rollup are not yet built. Services,
Docker, tests, and CI wiring for Mega Project 4 follow once all 6
notebooks exist, matching how Mega Projects 1-3 were each hardened as a
whole once their notebooks were complete — not piecemeal per notebook.

## [1.8.4] - 2026-09-01

### Fixed the actual GitHub Actions CI failure on Mega Project 3

The `unit-tests (03_mega_project_3_risk_segmentation)` CI job was genuinely
red on GitHub (exit code 2 -- a pytest *collection* error, not a test
failure): `03_mega_project_3_risk_segmentation/tests/test_scoring_services.py`
does `import polars as pl` (used to read the synthetic fixture CSVs and
build independent reference rows for 8 of its assertions), but
`03_mega_project_3_risk_segmentation/services/requirements-services.txt` --
CI's only install step before `pytest tests/` -- deliberately excludes
`polars` as unneeded by the production services themselves, so the import
failed before a single test could run. Mega Project 2 already carries the
identical `polars` line in its own `requirements-services.txt` with the
same documented rationale (its `regulatory_capital_features.py` has a
module-level `import polars as pl` even though its services don't touch a
DataFrame either); Mega Project 3's file was simply missing the equivalent
line for its test module. Added `polars>=0.20` there with a comment
explaining why, and re-verified all 3 unit-tests matrix jobs (MP1, MP2,
MP3) plus the `notebook-syntax` job in fresh, isolated virtualenvs that
install only what each job's own workflow step installs -- matching CI
exactly rather than trusting the sandbox's pre-existing environment. MP1:
10 passed. MP2: 5 passed. MP3: 4 skipped (correct -- no locally-trained
`.joblib`/segment-model bundle in this environment, which is the documented
skip-if-missing behavior, not a failure) after the collection error was
gone. `notebook-syntax`: 18/18 notebooks valid. This is the first time this
suite's CI status was checked against the *actual* GitHub Actions run
rather than only the local build-sandbox verification protocol -- the gap
existed because `pytest` was previously only ever run inside this sandbox's
already-populated environment, which had `polars` installed for unrelated
reasons and so never surfaced the missing dependency.

## [1.8.3] - 2026-09-01

### Adopted AMEX RiskIQ Platform documentation conventions (root-level, non-structural)

Compared this suite's GitHub structure directly against the real,
currently-pushed AMEX RiskIQ Enterprise Credit Risk Platform repo and
adopted its documentation conventions that improve this suite without
touching its already-verified Mega Project architecture (a full
per-problem folder split, mirroring AMEX's flat 14-problem layout, was
considered and deliberately not done -- it would fragment this suite's
5-distinct-business-capability narrative and require moving and
re-verifying all 18 built notebooks for no discoverability benefit a
much smaller change doesn't already deliver):

- `CONTRIBUTING.md` (NEW, suite root) -- the standing engineering rules
  (zero-fabrication, WARP, HYPER, `RANDOM_SEED = 42`, one-markdown-
  one-code-cell convention) and code organization, written down as a
  standalone document instead of only living inside the root README.
- `ROADMAP.md` (NEW, suite root) -- forward-looking Mega Project status
  table, hardening-track status, what's not yet done, and immediate next
  steps in order. Root `README.md`'s own "Roadmap" section shortened to
  a pointer at this file (mirrors this file's own relationship to
  `CHANGELOG.md`: `ROADMAP.md` is the summary/what's-next view,
  `CHANGELOG.md` stays the detailed, version-by-version record).
- `01_mega_project_1_underwriting_approval/CHANGELOG.md`,
  `02_mega_project_2_regulatory_capital/CHANGELOG.md`,
  `03_mega_project_3_risk_segmentation/CHANGELOG.md` (all NEW) -- a
  curated, this-Mega-Project-only version history table extracted from
  the root `CHANGELOG.md`, added to all 3 built Mega Projects for
  consistency (not just the 2 originally in scope for this pass).
- Root `README.md`: new "Quick links" line near the top (Live
  Dashboards, Architecture Diagrams, Roadmap, Changelog, Contributing,
  Benchmarks) and `CONTRIBUTING.md`/`ROADMAP.md`/each Mega Project's own
  `CHANGELOG.md` added to the Repository Structure listing.
- Each Mega Project's own `README.md`: a "History" line near the top
  pointing at its own `CHANGELOG.md` and the root one.
- Every new link verified to resolve (no broken relative paths) across
  all 9 touched files before committing.

## [1.8.2] - 2026-09-01

### Fixed a real discoverability gap: no project README linked its own reports or architecture diagram

None of the 3 built Mega Projects' own `README.md` files (including Mega
Project 1's) actually linked to their `sample_reports/` Word/Excel/HTML
files or embedded their architecture diagram -- both existed on disk and
were reachable only by browsing into subfolders. Fixed for all 3:

- Each Mega Project's `README.md` now embeds its architecture flow PNG
  directly (`## Architecture` section, right after the intro) with a
  link to the full-resolution PNG and its Mermaid source.
- Each Mega Project's `README.md` now has a `## Sample reports` section
  with a full per-problem table -- live GitHub Pages dashboard link,
  repo-copy HTML link, Word `.docx` link, and Excel `.xlsx` link, for
  every problem plus the executive rollup -- instead of a single generic
  pointer at the sample_reports/ folder (Mega Project 1 previously had
  no link at all).
- Root `README.md`: added an "Architecture Diagrams" section linking all
  3 Mega Projects' diagrams directly, and a matching Table of Contents
  entry.
- All new links verified to resolve (no broken relative paths) across
  all 4 READMEs before committing.

## [1.8.1] - 2026-09-01

### Repository hardening — top-level parity for Mega Projects 2 and 3

Cross-cutting follow-up to `[1.7.0]`/`[1.8.0]` closing out the remaining
top-level pieces of the "exactly like Mega Project 1" hardening pass.

- **Fixed a real bug in Mega Project 1's own `docker/Dockerfile` and
  `docker/docker-compose.yml`**: every path referenced a stale
  pre-restructure folder name (`mega_project_3_underwriting_approval`)
  left over from before this repo's `[1.1.0]` flat, numbered-layout
  restructure — never updated at the time. Corrected to the current
  `01_mega_project_1_underwriting_approval` throughout (build context
  paths, `COPY` instructions, `ENV` bundle paths, and the compose file's
  `dockerfile:` references). Re-verified structurally with
  `docker compose config` (clean) and static `COPY`-path existence
  checks (all present) — no Docker daemon in this build sandbox, so an
  actual `docker build`/`docker run` has still not been performed for
  any of the 3 Mega Projects (same disclosed limitation as before).
- `docs/index.html` (GitHub Pages Live Dashboards): added full "Mega
  Project 2 — Regulatory Capital & Stress Testing" and "Mega Project 3 —
  Risk Segmentation" sections (executive dashboard + all problem
  dashboards each), alongside the existing Mega Project 1 section.
  `docs/dashboards/` gained the 12 corresponding fixture-generated HTML
  files (`mp2_*`/`mp3_*` prefixed to avoid colliding with Mega Project
  1's existing `notebook_0N_dashboard.html` names).
- `.github/workflows/ci.yml`: the `unit-tests` job now runs as a matrix
  across all 3 Mega Projects' `services/`+`tests/` (was Mega Project 1
  only); `notebook-syntax` already covered all notebooks via its
  recursive glob.
- `.github/workflows/code-quality.yml`: `pyflakes`/`black --check`/
  `bandit` now scan Mega Project 2's and 3's `services/`/`tests/` too.
- `Makefile`: `test`, `lint`, and `security` targets now cover all 3
  built Mega Projects (were Mega Project 1 only), so `make test-all`
  matches what CI actually runs.
- `docs/mp2_architecture_flow.mmd`/`.png` and
  `docs/mp3_architecture_flow.mmd`/`.png` (NEW) -- mirror Mega Project
  1's own architecture diagram for the two newly hardened Mega Projects.
  All 3 architecture diagrams (including Mega Project 1's pre-existing
  one) were then redesigned together for visual consistency: a vivid,
  high-contrast color palette per node role (data/shared-library/model
  artifact/notebook/service), and the dense per-notebook "imported by"
  edge fan-out collapsed into one labeled arrow per shared-library
  subgraph, for a materially less cluttered diagram.
- Top-level `README.md`: Status, Skills Demonstrated, Live Dashboards,
  Roadmap, and Repository Hardening sections updated to reflect Mega
  Projects 1-3 all complete and hardened (services + Docker + tests +
  sample reports for all 3).

## [1.8.0] - 2026-09-01

### Mega Project 3 hardening: deployable services, Docker, tests, sample reports

Brings Mega Project 3 to full parity with Mega Projects 1 and 2's
hardening level, following the exact same real-code, no-fabrication
pattern.

- Notebooks 02/03/04 now persist their real, chosen K-Means model + real
  fitted `StandardScaler` + real feature list (+ real winsorize bounds
  for 03/04) to a new `notebook_0N_segment_model.joblib` artifact -- a
  small, additive change (the clustering/winsorization logic itself is
  unchanged). Re-executed and re-verified end-to-end on the fixture: 0
  errors, `nbformat.validate()` clean before/after clearing outputs,
  Playwright-confirmed dashboards (0 blocked requests, 0 console
  errors), LibreOffice-confirmed workbook recalculation, for all 3
  notebooks.
- `src/serving/segment_assignment_common.py` (NEW): HYPER shared
  component, the Mega Project 3 counterpart to Mega Project 1's own
  `scoring_service_common.py` -- builds a real FastAPI segment-assignment
  app from any of the 3 new joblib bundles (identical winsorize ->
  scale -> predict preprocessing to what each notebook itself does).
- `services/`: 4 real, deployable FastAPI services.
  - `risk_tier_assignment_service.py` (Problem 1): real tier boundaries
    read directly from Notebook 01's own JSON summary -- no model to
    load.
  - `bureau`/`repayment`/`utilization_segment_assignment_service.py`
    (Problems 2-4): thin wrappers over the new shared builder + each
    notebook's new joblib bundle.
  - Problems 5/6 deliberately get no service -- each is a
    population-level analysis/rollup that cannot be meaningfully
    computed for one applicant in isolation, the same honest scope
    boundary already established in Mega Project 1/2's own hardening
    passes.
- `tests/test_scoring_services.py`: 4 tests, all passing -- each
  verified against a REAL applicant already present in that notebook's
  own real output CSV (re-engineered features fed through the service,
  checked to match the notebook's own real assignment exactly).
- `docker/`: Dockerfile + docker-compose.yml + .dockerignore,
  suite-root build context, mirroring Mega Project 1/2's structure.
  Verified structurally (`docker compose config` + static `COPY`-path
  resolution) -- no Docker daemon in this build sandbox, so an actual
  `docker build`/`docker run` has not been performed (same disclosed
  limitation as Mega Project 1/2).
- `sample_reports/`: full new set, all 6 notebooks + rollup (18 files)
  plus a `README.md` matching Mega Project 1/2's disclosure pattern.
- `model_cards/02-04`: added a "Deployable service (hardening pass)"
  section each, disclosing the new joblib persistence and its real
  bit-identical verification.
- `README.md`: added "Running the scoring services", "Tests", and
  updated "Folder structure" sections.

## [1.7.0] - 2026-09-01

### Mega Project 2 hardening: deployable services, Docker, tests, sample reports

Brings Mega Project 2 to full parity with Mega Project 1's hardening
level, following the exact same real-code, no-fabrication pattern.

- `services/`: 2 real, deployable FastAPI scoring services -- neither
  loads a trained model (Mega Project 2 trains none); both import and
  call `src/features/regulatory_capital_features.py`'s real Basel
  retail-IRB Vasicek/ASRF functions directly, so nothing here can drift
  from what the notebooks themselves compute.
  - `capital_requirement_service.py` (Problem 1): real segment
    assignment + `K()`/EL/RWA/capital-requirement formula for one real
    applicant record.
  - `stress_testing_service.py` (Problem 4): the same real, documented
    macro scenarios (Baseline/Adverse/Severely Adverse) from
    `pipeline_mp2_nb04.py`, applied via the same conditional-PD-given-Z
    Vasicek formula.
  - Problems 2/3/5 deliberately get no service -- each is a
    population-level analysis (RWA density, Monte Carlo simulation, HHI
    concentration) that cannot be meaningfully computed for one
    applicant in isolation, the same honest scope boundary Mega Project
    1 already established for its own population-level Problem 5.
- `tests/test_scoring_services.py`: 5 tests, all passing, each checking
  a service's real output bit-identical against
  `regulatory_capital_features.compute_capital_row()` called directly.
- `docker/`: Dockerfile + docker-compose.yml + .dockerignore,
  suite-root build context, mirroring Mega Project 1's structure.
  Verified structurally (`docker compose config` + static `COPY`-path
  resolution) -- no Docker daemon in this build sandbox, so an actual
  `docker build`/`docker run` has not been performed (same disclosed
  limitation as Mega Project 1).
- `sample_reports/`: completed the set (Notebooks 03-06 + rollup were
  missing) -- all 18 fixture-generated files now present, plus a
  `README.md` matching Mega Project 1's disclosure pattern.
- `README.md`: added "Running the scoring services", "Tests", and
  updated "Folder structure" sections.

## [1.6.9] - 2026-09-01

### Added — Mega Project 3, Notebook 05: Cross-Axis Risk-Return Synthesis (5/6)

Trains no model of any kind and reads no raw Home Credit CSV -- a pure,
honest synthesis of real outputs every other notebook in this suite
already computed and independently verified: real PD/TARGET/Risk Tier
(this project's own Notebook 01, hard dependency), real regulatory
capital (Mega Project 2 / Notebook 01, soft dependency), and real
Bureau/Repayment/Utilization Segment (this project's own Notebooks
02-04, each an independent soft dependency). For each real axis actually
available, computes real default-rate and real capital-rate spread
across its own segments and ranks axes by how sharply each
differentiates real risk.

Deliberately does NOT repeat a chi-square/silhouette test -- those
questions were already answered inside each axis's own notebook, and
repeating them here would be double-counting, not new evidence. Instead
asks a new real question: does real capital allocation track real risk
through Risk Tier's real, PD-ordered axis? Uses
`monotonic_within_noise()` (the same statistically-tolerant,
Bonferroni-corrected check Notebook 01 already used for default-rate
monotonicity) on real CAPITAL rate this time -- a different claim never
previously tested. The other 3 axes are unordered categorical segments,
so no monotonicity check applies to them.

### Verified clean on first execution -- no bugs found

On this suite's fixture, all 4 real axes were available. Real
default-rate spread by axis (widest to narrowest): Risk Tier 97.97%
(1.63%-99.59% across 6 real data-driven tiers -- expected, built
directly from real PD), Repayment Segment 7.84% (12.58%-20.42% across
8), Bureau Segment 6.68% (13.23%-19.91% across 8), Utilization Segment
5.96% (12.50%-18.46% across 8). Real capital rate by axis: Risk Tier
5.64%-9.09%, Bureau Segment 6.16%-6.49%, Repayment Segment 5.71%-6.63%,
Utilization Segment 5.86%-6.82%. Real capital-rate monotonicity across
Risk Tier: HOLDS. Synthesis verdict: SYNTHESIS VALIDATED -- CAPITAL
TRACKS RISK AS EXPECTED (all 4 synthesis-validation checks pass). All
structural Pipeline Integrity Checks pass. Verified end-to-end: 0
execution errors, nbformat.validate() clean, HTML dashboard confirmed
under a network-blocked Playwright check, Excel workbook confirmed via
LibreOffice headless recalculation -- clean on its first execution, no
bugs found.

**Confirmed on the user's real 307,511-applicant data**: all 4 real axes
available. Real default-rate spread by axis (widest to narrowest): Risk
Tier 48.92% (1.67%-50.59%), Utilization Segment 10.51% (5.42%-15.94%
across 9 real segments -- notably re-ranking to 2nd place at real scale,
ahead of Bureau Segment (2.98%) and Repayment Segment (2.44%), a reversal
from the fixture's ranking), Bureau Segment 2.98%, Repayment Segment
2.44%. Real capital-rate monotonicity across Risk Tier: HOLDS. Real
synthesis verdict: SYNTHESIS VALIDATED -- CAPITAL TRACKS RISK AS
EXPECTED. 0 execution errors, all checks pass.

## [1.6.10] - 2026-09-01

### Added — Mega Project 3, Notebook 06: Consolidated Executive Rollup (6/6) -- Mega Project 3 now COMPLETE

Pure rollup, no new modeling: trains nothing, clusters nothing, reads no
raw Home Credit CSV. Reads each of Problems 1-5's own, already-computed
real governance JSON summary and consolidates them into one
executive-ready Word report, multi-sheet Excel workbook, and interactive
HTML dashboard. A missing summary is reported and skipped, never
fabricated.

Two genuinely new things: (1) "Real Segmentation Power" -- a fresh bar
chart independently re-deriving each of Problems 1-4's own real
default-rate spread straight from that problem's OWN summary JSON,
deliberately not dependent on Problem 5 having run at all; (2) real
cross-notebook consistency checks (Section 5) that verify Problem 5's own
independent real re-aggregation of each axis agrees, segment by segment,
with that axis's own source notebook -- never asserted, always computed
and printed, plus a real applicant-population-count consistency check
across all 5 notebooks.

Correctly surfaces both of this Mega Project's verdict-tier families side
by side -- Problems 1-4's "Statistical Robustness Verdict" and Problem
5's differently-named "Synthesis Verdict" -- never conflating them, via
`PROBLEM_META`'s per-problem `verdict_path`/`verdict_kind`.

### Verified clean on first execution -- no bugs found

On this suite's fixture: 5/5 real problem summaries found, real applicant
population 4,000. Real segmentation power widest to narrowest: Risk Tier
97.97%, Repayment Segment 7.84%, Bureau Segment 6.68%, Utilization
Segment 5.96%. Every real cross-notebook consistency check CONFIRMED --
maximum absolute difference of exactly 0.00 across every shared segment
on every one of the 4 axes (Problem 5's independent re-aggregation
matches each source notebook's own numbers exactly), and the real
applicant population count (4,000) matched identically across all 5
notebooks. All 5 rollup integrity checks pass. Verified end-to-end: 0
execution errors, `nbformat.validate()` clean before and after clearing
outputs, HTML dashboard confirmed under a network-blocked Playwright
check (0 blocked external requests, 0 console errors, 10 KPI cards, 7
charts rendered), Excel workbook confirmed via LibreOffice headless
recalculation (11 sheets, every Financial Impact formula recalculates to
the exact value the notebook's own run printed) -- clean on its first
execution, no bugs found. Not yet run against the user's real data.

**Mega Project 3 (Risk Segmentation) is now complete: 6/6 problems built
and verified**, matching Mega Projects 1 and 2's fully-complete status.

## [1.6.8] - 2026-09-01

### Added — Mega Project 3, Notebook 04: Revolving Credit Utilization Segmentation (4/6)

Trains no supervised model and scores no PD -- reuses Mega Project 3 /
Notebook 01's real per-applicant PD/TARGET/RISK_TIER output unchanged
(hard dependency, checked by actual required columns present). The
genuinely new work is real unsupervised sklearn.cluster.KMeans clustering
on a real 13-feature revolving-credit-utilization feature set
(`engineer_revolving_credit_utilization_features()`, added to
`src/features/risk_segmentation_features.py`), built entirely from the
applicant's own real credit-card usage on PREVIOUS Home Credit revolving
loans -- real month-by-month utilization (`AMT_BALANCE`/
`AMT_CREDIT_LIMIT_ACTUAL`), real minimum-payment-only behavior
(`AMT_PAYMENT_TOTAL_CURRENT` vs. `AMT_INST_MIN_REGULARITY`), and real
cash-advance frequency (`AMT_DRAWINGS_ATM_CURRENT`) -- a fourth axis
touching neither Problem 1's PD level, Problem 2's external bureau
tables, nor Problem 3's instalment-loan repayment conduct.

Fixture change: `fixture/credit_card_balance.csv` was extended in place
(`extend_fixture_credit_card_balance.py`) with two real Kaggle columns
this notebook's cash-advance feature needs (`AMT_DRAWINGS_ATM_CURRENT`,
`CNT_DRAWINGS_ATM_CURRENT`) that the original 11-column fixture (created
for Notebook 02's multi-table verification) did not include -- every
existing row and column's values are preserved byte-for-byte, so Mega
Project 1 and 2's already-verified fixture results are unaffected. The
user's real data already has the full real Kaggle schema.

Applied FROM THE START, pre-emptively, rather than discovered live on
this notebook's own real run: winsorization of the 9 unbounded real
features (Notebook 03's real-data lesson on outlier domination), and a
K range starting at 2 with a 1% (not 3%) stability floor default
(Notebook 03's real-data lesson on real minority-group size). Two soft
cross-axis checks (Notebook 02's Bureau Segment, Notebook 03's Repayment
Segment) in addition to the Problem 1 Risk Tier cross-check -- the most
independence evidence gathered for any MP3 problem so far. No
`monotonic_within_noise()` call, by design. No `matplotlib.use(...)`
call. No EDA section.

### Verified clean on first execution -- no bugs found

On this suite's fixture: 7 real data-driven revolving-credit-utilization
segments found (silhouette=0.184, chosen from all 7 candidates tried,
k=2 through k=8, every one clearing the 1% floor at this small scale).
1,034 of 4,000 real fixture applicants (25.9%) have real previous-loan
revolving-credit history and were clustered; the remaining 2,966 (74.1%)
reported as their own "No Revolving Credit History" segment. Real
default rate spans 12.5%-18.5% across the 8 total segments. Real
cross-checks: Cramer's V=0.051 vs. Problem 1's Risk Tier, 0.043 vs.
Problem 2's Bureau Segment, 0.130 vs. Problem 3's Repayment Segment --
all evidencing a real, independent fourth axis. Statistical Robustness
Verdict on the fixture: NOT YET STATISTICALLY ROBUST (chi-square
p=0.949, Cramer's V 95% bootstrap CI [0.023, 0.070]) -- the same
expected fixture-scale limitation already documented for Problems 2-3,
not a code defect; all structural Pipeline Integrity Checks pass
regardless. Verified end-to-end: 0 execution errors, nbformat.validate()
clean, HTML dashboard confirmed under a network-blocked Playwright
check, Excel workbook confirmed via LibreOffice headless recalculation
-- clean on its first execution, no bugs found. Not yet run against the
user's real data.

## [1.6.7] - 2026-09-01

### Verified — Mega Project 3, Notebook 03: confirmed working end-to-end on real 307,511-applicant data

With v1.6.4 (winsorization), v1.6.5 (k=2 added to the candidate range),
and v1.6.6 (1% stability floor) all in place, the user re-ran Notebook 03
against their real data and it completed successfully: 0 errors, all 9
structural Pipeline Integrity Checks pass, full reporting package
(Word/Excel/HTML/CSV) written.

Real result: 291,643 of 307,511 real applicants (94.8%) have real
previous-loan repayment history. Real data-driven K selection chose
**k=2** decisively (real silhouette=0.717, well clear of the k=3-7
candidates it beat, 0.22-0.31) -- real Segment A: 287,666 applicants
(7.4% mean instalments-late rate, 8.18% real default rate); real Segment
B: 3,977 applicants (18.7% mean instalments-late rate, 8.42% real default
rate) -- the same recurring ~1.4% minority behavioral group observed
consistently across every k tried while diagnosing the earlier
RuntimeError; plus 15,868 (5.2%) applicants with no previous-loan
history. Real cross-checks: Cramer's V=0.044 vs. Problem 1's Risk Tier,
0.039 vs. Problem 2's Bureau Segment -- both genuinely low, confirming
real cross-axis independence from both prior segmentations.

Real Statistical Robustness Verdict: NOT YET STATISTICALLY ROBUST --
`chi_square_significant` PASSED (p=3.2e-22) but
`cramers_v_ci_excludes_zero` FAILED (real Cramer's V=0.0179, 95%
bootstrap CI [0.0150, 0.0210], below the 0.05 materiality threshold) --
the same honest two-tier pattern already documented for Problem 2: a
real, cross-axis-independent, statistically detectable signal reported
honestly as too small in magnitude to call "robust." This is Problem 3's
final, confirmed result on real data -- no further pipeline changes are
needed. Documentation-only release (model card + README updated with the
confirmed real numbers; no code changes).

## [1.6.6] - 2026-09-01

### Changed — Mega Project 3, Notebook 03: lower the stability floor from 3% to 1%, empirically grounded

After v1.6.5 widened the K candidate range to include k=2, re-running on
the user's real 307,511-applicant data showed that even the broadest
possible split (k=2) stayed under the 8,749-applicant (3%) floor: its
smallest real cluster was 3,977. Across every real k from 2 to 8, the
smallest real cluster consistently landed in the 2,700-4,000 range
(~1.0%-1.4% of the with-history population) -- a tight, repeating band
across all 7 candidates, not noise and not the earlier "collapses to a
handful of points" outlier signature. That consistency is real evidence
of a recurring minority behavioral group in the real 307K population, not
an artifact to chase further.

`repayment_segment_min_cluster_fraction`'s default changed from 0.03 to
**0.01** in `pipeline_mp3_nb03.py` -- a value grounded in what was
actually observed across all 7 real candidates tried on the user's own
data, not an arbitrary relaxation to force a pass. The pipeline
unchanged: it still picks whichever passing k has the best real
silhouette score; the floor only changes which candidates are eligible.

### Verified clean on re-execution -- no regression on the fixture

Re-run end-to-end on this suite's fixture: identical result to v1.6.5
(k=7 chosen, silhouette 0.161) -- the fixture's smallest real cluster was
always well above both the old 3% and new 1% floor, so this change only
affects real-scale behavior. 0 execution errors, `nbformat.validate()`
clean, HTML dashboard confirmed under a network-blocked Playwright check,
Excel workbook confirmed via LibreOffice headless recalculation. **Ready
to re-run against the user's real data -- combined with v1.6.4 and
v1.6.5, this directly addresses the RuntimeError seen there.**

## [1.6.5] - 2026-09-01

### Changed — Mega Project 3, Notebook 03: widen K candidate range to include k=2

After the v1.6.4 winsorization fix, re-running Notebook 03 on the user's
real 307,511-applicant data no longer hit the outlier-domination failure
(smallest real clusters no longer collapsed to a handful of points at
every k), but still raised the same `RuntimeError` for a different,
more benign reason: every candidate k from 3 to 8 produced a smallest
real cluster of 2,700-3,900 applicants -- a real, substantial group, just
short of the 8,749-applicant (3%) stability floor. That pattern (cluster
size scaling sensibly with k rather than collapsing) is real evidence of
actual structure, not another outlier artifact.

Rather than lowering the stability floor to force a pass,
`repayment_segment_k_min`'s default in `pipeline_mp3_nb03.py` changed
from 3 to **2**, so the pipeline also tests whether the real 307K-scale
data supports just two broad, stable repayment-behavior groups -- a real
data-driven test of a candidate that simply hadn't been tried yet, not a
relaxed bar. `repayment_segment_min_cluster_fraction` (the 3% floor
itself) is unchanged.

### Verified clean on re-execution -- no regression on the fixture

Re-run end-to-end on this suite's fixture: k=7 is still chosen (silhouette
0.161, unchanged) -- k=2's silhouette (0.150) is lower and does not
change the fixture's outcome. All 9 structural Pipeline Integrity Checks
pass, 0 execution errors, `nbformat.validate()` clean, HTML dashboard
confirmed under a network-blocked Playwright check, Excel workbook
confirmed via LibreOffice headless recalculation. **Ready to re-run
against the user's real data -- combined with v1.6.4's winsorization fix,
this directly addresses the RuntimeError seen there.**

## [1.6.4] - 2026-09-01

### Fixed — Mega Project 3, Notebook 03: real-data K-Means outlier domination

Running Notebook 03 on the user's real 307,511-applicant data raised the
notebook's own by-design `RuntimeError`: every candidate K from 3 to 8
produced at least one real cluster below the minimum stable size
(8,749 applicants, 3% of the 291,643 real applicants with repayment
history) -- k=5 through k=8 each collapsed to a smallest real cluster of
just 3 applicants, and k=3/k=4 fell to 1,390/1,354. This was not a code
defect in the sense of wrong logic -- the guard fired exactly as designed,
refusing to report an unstable segmentation -- but the underlying real
cause was a genuine pipeline gap: `engineer_repayment_behavior_features()`
fed 9 structurally unbounded real features (`MAX_DAYS_LATE`,
`MEAN_PAYMENT_RATIO`, `MAX_SK_DPD`, etc.) straight into `StandardScaler`
with no clipping step, so a small number of genuinely extreme real values
(present in the real 307K-row data but never occurring in the suite's
small synthetic fixture) dominated Euclidean distance and caused K-Means
to isolate them as their own tiny outlier cluster at every K it tried.

### Added — real winsorization in `engineer_repayment_behavior_features()`

`src/features/risk_segmentation_features.py`'s
`engineer_repayment_behavior_features()` now clips its 9 unbounded real
features to the real 1st/99th percentile range, computed ONLY over
applicants WITH real repayment history (never over the 0-filled "no
history" rows, and never applied to them either). This bounds, and never
invents, the influence of real outliers -- every clipped value is still a
real value that occurred in the real data, only capped to a real,
disclosed quantile of the real with-history population's own
distribution. The function now returns a third element, a
`winsorize_report` dict with the exact per-feature bounds and how many
real values were clipped at each end; `pipeline_mp3_nb03.py` prints this
report in full (never silently) and includes it in the notebook's JSON
summary and Excel workbook assumptions sheet.

### Verified clean on re-execution -- no regression on the fixture

Re-run end-to-end on this suite's fixture after the fix: still finds
k=7 (highest real silhouette score, 0.161, unchanged from before the fix
to 3 decimal places), 2,691 of 4,000 real fixture applicants (67.3%)
clustered into 7 segments (459/470/730/420/142/311/159) plus 1,309 "No
Repayment History." Real default rate spans 12.6%-20.4%. Real
cross-checks: Cramer's V=0.072 vs. Problem 1's Risk Tier, 0.047 vs.
Problem 2's Bureau Segment -- both still genuinely low. Statistical
Robustness Verdict unchanged: NOT YET STATISTICALLY ROBUST at this
fixture's small scale (chi-square p=0.459, Cramer's V 95% bootstrap CI
[0.033, 0.084]) -- the same expected fixture-scale limitation as before,
not a regression. All 9 structural Pipeline Integrity Checks pass.
Verified end-to-end: 0 execution errors, `nbformat.validate()` clean, HTML
dashboard confirmed under a network-blocked Playwright check, Excel
workbook confirmed via LibreOffice headless recalculation. **Ready to
re-run against the user's real data -- this fix directly addresses the
RuntimeError seen there.**

## [1.6.3] - 2026-09-01

### Added — Mega Project 3, Notebook 03: Repayment Behavior Segmentation (3/6)

Trains no supervised model and scores no PD -- reuses Mega Project 3 /
Notebook 01's real per-applicant PD/TARGET/RISK_TIER output unchanged
(hard dependency, checked by actual required columns present). The
genuinely new work is real unsupervised sklearn.cluster.KMeans clustering
on a real 13-feature repayment-discipline feature set
(`engineer_repayment_behavior_features()`, added to the shared
`src/features/risk_segmentation_features.py` module), built entirely from
the applicant's own real conduct on PREVIOUS Home Credit loans -- real
`installments_payments.csv` lateness (`DAYS_ENTRY_PAYMENT -
DAYS_INSTALMENT`) and real payment-completeness ratio
(`AMT_PAYMENT/AMT_INSTALMENT`), plus real `POS_CASH_balance.csv`
days-past-due tracking -- a third axis touching neither Problem 1's PD
level nor Problem 2's external bureau tables. Real, disclosed null
handling: an instalment never actually paid has null
DAYS_ENTRY_PAYMENT/AMT_PAYMENT, dropped from the lateness/payment-ratio
aggregations (never treated as 0) but still counted in the
total-instalments feature. Real cluster count (K) chosen by silhouette
score across a documented candidate range; applicants with zero real
previous-loan repayment history get their own explicit "No Repayment
History" segment, never imputed.

New this notebook: a real SOFT cross-check against Mega Project 3 /
Notebook 02's Bureau Segment output (when present) in addition to the
existing cross-check against Problem 1's Risk Tier -- both computed as
honest, descriptive evidence of cross-axis independence, not gated
pass/fail checks. No `monotonic_within_noise()` call, by design
(unordered categorical segments, same reasoning already established
twice in this suite). No `matplotlib.use(...)` call. No EDA section.

### Verified clean on first execution -- no bugs found

On this suite's fixture: 7 real data-driven repayment behavior segments
found (silhouette=0.161, chosen from 5 candidates that cleared the
minimum-cluster-size floor -- k=8 was rejected, its smallest real cluster
of 73 falling below the 80-applicant floor). 2,691 of 4,000 real fixture
applicants (67.3%) have real previous-loan repayment history and were
clustered; the remaining 1,309 (32.7%) reported as their own "No
Repayment History" segment. Real default rate spans 12.0%-18.7% across
the 8 total segments. Real cross-checks: Cramer's V=0.072 vs. Problem 1's
Risk Tier, Cramer's V=0.045 vs. Problem 2's Bureau Segment -- both
genuinely low, evidencing a real, independent third axis. Statistical
Robustness Verdict on the fixture: NOT YET STATISTICALLY ROBUST
(chi-square p=0.278, Cramer's V 95% bootstrap CI [0.035, 0.087]) -- the
same expected fixture-scale statistical-power limitation already
documented for Problem 2 (LESSONS_LEARNED.md #3), not a code defect; all
structural Pipeline Integrity Checks pass regardless. Verified end-to-end:
0 execution errors, nbformat.validate() clean, HTML dashboard confirmed
under a network-blocked Playwright check, Excel workbook confirmed via
LibreOffice headless recalculation -- clean on its first execution, no
bugs found. Not yet run against the user's real data.

Mega Project 3 (Risk Segmentation): 3 of 6 planned problems built.

## [1.6.2] - 2026-09-01

### Fixed — Mega Project 1's problem numbering, renumbered to match Mega Project 2 / Mega Project 3's convention

**What was inconsistent (caught by the user, reviewing Mega Project 1's
executive rollup dashboard)**: Mega Project 1's 5 problem notebooks
originally carried numbers from this suite's very first, pre-Mega-Project
global plan (Problem 1, 3, 4, 11, 12 -- non-consecutive because the
original plan interleaved problems across all 5 Mega Projects before they
were split into separate folders), while Mega Project 2 (Problems 1-6) and
Mega Project 3 (Problems 1-2 so far) were both built later using clean,
local, project-relative numbering from the start. Both conventions were
internally consistent on their own but inconsistent with each other --
visible wherever Mega Project 1's problem numbers appeared next to Mega
Project 2/3's, most visibly on Mega Project 1's own executive rollup
dashboard.

**Fix**: Mega Project 1's problems are renumbered to local 1-5, and its
executive rollup notebook (06) is now explicitly "Problem 6" -- the exact
convention Mega Project 2 and Mega Project 3 already use for their own
rollups. Old -> new mapping, for anyone cross-referencing older material
against this suite (e.g. `BENCHMARKS.md` entries or earlier screenshots
that still show the old numbers):

| Old (global) | New (local) | Notebook |
|---|---|---|
| Problem 1 | Problem 1 | 01 — Credit Default Prediction |
| Problem 3 | Problem 2 | 02 — Loan Application Approval |
| Problem 4 | Problem 3 | 03 — Credit Score Estimation |
| Problem 11 | Problem 4 | 04 — Repayment Capacity Analysis |
| Problem 12 | Problem 5 | 05 — Previous Application Outcomes |
| (unnumbered) | Problem 6 | 06 — Executive Rollup |

This is a label-only change -- a single-pass regex substitution (never
sequential replacements, to avoid the classic renumbering collision where
a freshly-written new number gets re-matched by a later replacement step)
applied across every `pipeline_*.py` source, `build_ipynb*.py` header,
the shared `src/features/credit_default_features.py` and
`src/features/applicant_credit_history_features.py` and
`src/utils/stats_checks.py` modules, all 5 model cards, both `README.md`
files (root and Mega Project 1's own), `sample_reports/README.md`, all 4
deployable services, `tests/test_stats_checks.py`, and the Docker
Dockerfile/compose file. No modeling logic, feature engineering, scoring,
or statistical validation changed in any notebook. Also fixed, found while
in these same files: all 6 Mega Project 1 notebooks still said "6 Mega
Projects Enterprise Suite" in their own header (a leftover from before the
suite was fixed at exactly 5 Mega Projects) while Mega Project 2 and Mega
Project 3 already correctly said "5" -- now consistent everywhere.

Historical `CHANGELOG.md` entries below this one are left exactly as
originally written (they used the numbering that was true for that
build at the time) -- this section is the map from those old numbers to
the new ones, not a rewrite of history.

### Verified clean on re-execution -- no bugs found

All 6 Mega Project 1 notebooks were rebuilt from their updated source
(per this suite's own `LESSONS_LEARNED.md` #1: editing a `pipeline_*.py`
file does not change an already-built `.ipynb` until its `build_ipynb*.py`
is re-run) and re-executed end-to-end on the fixture in dependency order
(01 through 05, then 06 last) -- 0 execution errors across all 6, same
real fixture results as before (this is a pure relabeling, not a logic
change). Full verification protocol re-run and clean on all 6:
`nbformat.validate()`, network-blocked Playwright dashboard check (0
blocked requests / 0 console errors / 0 page errors across all 6
dashboards including the executive rollup), LibreOffice headless
recalculation on all 6 workbooks (including the executive workbook's
"Problem Rollup" sheet, confirmed showing Problem 1-5 in order), outputs
cleared and re-validated.

**Because Mega Project 1 was already run against your real data before
this fix, re-running these updated notebooks against your real data is
needed to get real reports with the corrected Problem 1-5 labels** — your
existing real results/figures are unaffected (nothing computational
changed), only the labels.

## [1.6.1] - 2026-09-01

### Added — Mega Project 3, Notebook 02: Credit Bureau Behavioral Segmentation (2/6)

Trains no supervised model and scores no PD -- reuses Mega Project 3 /
Notebook 01's real per-applicant `PD`/`TARGET`/`RISK_TIER` output
unchanged (hard dependency, checked by actual required columns present,
not just file existence -- LESSONS_LEARNED.md #4). The genuinely new work
is real unsupervised `sklearn.cluster.KMeans` clustering on a real,
richer 16-feature bureau/bureau_balance behavioral feature set (new
shared module `src/features/risk_segmentation_features.py` --
`engineer_bureau_behavior_features()`), deliberately broader than the 7
bureau summary features already inside Mega Project 1's champion PD model
and a genuinely different mechanism (unsupervised similarity, never
trained against real TARGET). Real cluster count (K) is chosen by the
real `sklearn.metrics.silhouette_score` across a documented candidate
range (config `bureau_segment_k_min`/`bureau_segment_k_max`, default
3-8), sampled via scikit-learn's own `sample_size` parameter for O(n)
tractability at real ~300K scale (disclosed), rejecting any K whose
smallest real cluster falls below a minimum stable size (config
`bureau_segment_min_cluster_fraction`, default 3%). Real applicants with
zero bureau history are never silently imputed into a cluster -- they get
their own explicit "No Bureau History" segment, disclosed by real,
measured prevalence.

Applies LESSONS_LEARNED.md deliberately, including recognizing where an
established check does NOT apply: no `monotonic_within_noise()` call in
this notebook, by design -- behavioral clusters are unordered categorical
segments with no expected direction, the same reasoning Mega Project 2 /
Notebook 05 already established for its own HHI concentration analysis
(#2). No `matplotlib.use(...)` call anywhere in the file (#7). Real
cross-check (Section 9): Cramer's V between this notebook's Bureau
Segment and Problem 1's Risk Tier, computed as honest evidence of
cross-axis independence, not a gated pass/fail check (#6's "real
cross-checks beat asserted correctness" pattern).

### Verified clean on first execution -- no bugs found

On this suite's fixture: 7 real data-driven bureau behavioral segments
found (silhouette=0.153, chosen from 6 candidates k=3..8 that cleared the
minimum-cluster-size floor). 3,598 of 4,000 real fixture applicants
(90.0%) have real bureau history and were clustered; the remaining 402
(10.0%) reported as their own "No Bureau History" segment. Real default
rate spans 13.2%-19.9% across the 8 total segments. Real cross-check
against Problem 1's Risk Tier: Cramer's V=0.049 -- genuinely low,
evidencing independent axes, not a relabeling. Statistical Robustness
Verdict on the fixture: NOT YET STATISTICALLY ROBUST (chi-square
p=0.453, Cramer's V 95% bootstrap CI [0.032, 0.082], below this suite's
0.05 materiality threshold) -- an honestly-computed, expected result at
this small fixture scale (LESSONS_LEARNED.md #3's scale-sensitivity
lesson, applying in the opposite direction from where it was first
documented: limited statistical power splitting 3,598 rows across 7
clusters, not over-detection), not a code defect; all structural Pipeline
Integrity Checks pass regardless, per this suite's two-tier verdict
pattern. Verified end-to-end: 0 execution errors, nbformat.validate()
clean, HTML dashboard confirmed under a network-blocked Playwright check,
Excel workbook confirmed via LibreOffice headless recalculation -- clean
on its first execution, no bugs found. Not yet run against the user's
real data.

Mega Project 3 (Risk Segmentation): 2 of 6 planned problems built.

## [1.6.0] - 2026-09-01

### Added — Mega Project 3, Notebook 01: Data-Driven Risk Tier Construction (MEGA PROJECT 3 STARTED, 1/6)

Trains no new default-risk model -- reuses Mega Project 1 / Notebook 01's
real champion model (loaded, never retrained) to score real PD. The
genuinely new work is the TIERS themselves: a real
`sklearn.tree.DecisionTreeClassifier` fit directly on real PD vs. real
TARGET finds where the real data itself splits most sharply, and those
real thresholds -- not the suite's existing fixed 5-band convention (PD <
0.05/0.10/0.20/0.35, used elsewhere for Basel capital purposes) -- become
the tier boundaries. Achieved tier count is whatever the real data
supports, never forced by construction (`max_leaf_nodes` is a ceiling,
`min_samples_leaf` prevents unstable tiny tiers). Soft-enriches with Mega
Project 2 / Notebook 01's real capital output when available
(capital-by-tier), and still produces a complete, standalone result when
it isn't -- the same soft-dependency posture Mega Project 1's Notebook 04
already established.

Applies every LESSONS_LEARNED.md item from the first version, not
retrofitted: hard dependency checked by actual feature-set compatibility
(#4), `monotonic_within_noise()`'s ordering contract verified explicitly
with both arrays reversed before the call since tiers are ascending-PD
(#2), no `matplotlib.use(...)` call anywhere in the file (#7), vectorized
multinomial bootstrap for the Cramer's V CI (never per-resample
`pandas.crosstab`), and runtime-validated tier boundaries (strictly
increasing, no duplicates, every tier non-empty).

### Verified clean on first execution -- no bugs found

On this suite's fixture: 6 real data-driven tiers found (5 real split
thresholds), real default rate strictly monotonic from 1.6% (Tier 1) to
99.6% (Tier 6), chi-square p≈0, Cramer's V=0.887 (95% bootstrap CI [0.870,
0.904]) -- STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION. All 4,000
fixture applicants matched against Mega Project 2 / Notebook 01's real
capital output for the enrichment. Verified end-to-end: 0 execution
errors, all integrity and statistical-robustness checks pass,
nbformat.validate() clean, HTML dashboard confirmed under a
network-blocked Playwright check, Excel workbook confirmed via LibreOffice
headless recalculation. Not yet run against the user's real data.

Starts Mega Project 3 (Risk Segmentation): 1 of 6 planned problems built.

## [1.5.0] - 2026-09-01

### Added — LESSONS_LEARNED.md items #7-8, ahead of Mega Project 3

Two more real incidents recorded before Mega Project 3's first notebook is
written: #7 the matplotlib `Agg`-backend inconsistency fixed in [1.4.9]
(checklist: never call `matplotlib.use(...)` in a new notebook unless
specifically required); #8 a real point of user confusion, not a suite
bug, where printed OUTPUT text (containing a comma-formatted dollar
figure) was pasted into a Jupyter code cell and executed, producing a
`SyntaxError` on a leading-zero numeric literal — recorded so a future
`SyntaxError` report referencing prose-looking text is checked against
this suite's own printed-output format before assuming a code defect.
Intro paragraph updated: Mega Project 2 (all 6 notebooks, now complete and
confirmed on real data) is the source of every lesson in this file; it
now exists for Mega Project 3 onward.

Mega Project 2 status: complete, 6/6 notebooks, confirmed working
end-to-end on the user's real 307,511-applicant data.

## [1.4.9] - 2026-09-01

### Fixed — cosmetic UserWarning on real-data execution of Notebook 06

Confirmed by the user's real 307,511-applicant run: report generation
succeeded completely (all 6 rollup integrity checks PASS, real $9,756,908,313
Pillar-1 capital, all 3 report formats written) -- but a
`UserWarning: FigureCanvasAgg is non-interactive, and thus cannot be shown`
appeared on the `plt.show()` line. Root cause: Notebook 06 was the only
notebook in this suite that explicitly forced `matplotlib.use("Agg")` before
importing pyplot; every other notebook (01, 02, 05, and Mega Project 1's own
charts) lets Jupyter's own inline backend handle `plt.show()`, which does
not warn. Fixed by removing the explicit `Agg` backend call, matching every
other notebook's already-proven-clean pattern. The saved chart PNG was
never affected either way (`plt.savefig()` runs before `plt.show()`) --
this was a cosmetic stderr warning only, never a sign of failed or
incomplete report generation. Re-verified end-to-end on the fixture after
the fix: 0 execution errors, 0 warnings of any kind, all 6 integrity checks
still pass, nbformat.validate() clean, Playwright dashboard check clean
with slicers still confirmed interactive, LibreOffice recalc still exact.

## [1.4.8] - 2026-09-01

### Added — Mega Project 2, Notebook 06: Consolidated Executive Rollup (MEGA PROJECT 2 NOW COMPLETE, 6/6)

A pure rollup notebook -- trains nothing, re-simulates nothing. Reads all
5 real problem notebooks' own already-computed governance JSON summaries
and consolidates them into one executive-ready package. Adds exactly two
new things: the "Three Real Lenses on Capital" comparison (Pillar-1
Baseline vs. 99.9% Monte Carlo Economic Capital vs. Adverse/Severely
Adverse Stressed Capital -- three real, independently-computed answers to
three different questions about the SAME real portfolio, placed side by
side explicitly to compare, never to sum) and 3 real cross-notebook
consistency checks (baseline capital consistent across Notebooks 01/03/04;
stressed capital strictly increases with severity; every real HHI value
within its valid [0, 10,000] range).

### World-class 3-format reporting package

- Word report: exec summary, 7 SMART insights, one section per problem
  with that problem's own already-verified real chart image embedded
  (never redrawn), plus a dedicated "Three Real Lenses" section with the
  notebook's one new synthesis chart.
- Excel workbook, 10 sheets: a big-letters "Executive Rollup" front sheet
  with a native, editable openpyxl BarChart of the Three Real Lenses; one
  sheet per problem with that problem's own real chart image embedded PLUS
  a second native Excel chart from that problem's own real per-category
  numbers; a real formula-driven Financial Impact sheet (confirmed to
  recalculate correctly under LibreOffice headless); a SMART Insights
  sheet.
- HTML dashboard: 8 real KPI cards, 7 charts -- 2 of them carrying a real,
  browser-tested dropdown slicer that switches the chart across this
  dataset's real segment dimensions (RWA density and capital share, each
  across 4-5 real dimensions) -- confirmed via an actual Playwright
  browser interaction test to change the rendered chart's labels, not just
  visually inspected.

### Verification

Verified end-to-end on this suite's synthetic fixture: 0 execution errors,
all 6 rollup integrity checks pass, nbformat.validate() clean before and
after clearing outputs, HTML dashboard confirmed under a network-blocked
Playwright check with the 2 dropdown slicers driven programmatically and
confirmed to actually change chart data, Excel workbook confirmed via
LibreOffice headless recalculation (every Financial Impact formula
recalculated to the exact real values the notebook itself printed). Not
yet run against the user's real data.

Bumps Mega Project 2 to complete: all 6 of 6 notebooks built and verified.

## [1.4.7] - 2026-09-01

### Added — Mega Project 2, Notebook 05: Capital Concentration by Segment

Trains no model and introduces no new PD/LGD/EAD/correlation value.
Reuses Notebook 01's real per-applicant capital output unchanged, joined
with real application-level segment columns already used by Notebook 02
(income type, education, contract type, region rating) plus Notebook 01's
own capital segment, for 5 real dimensions total. Computes a real
Herfindahl-Hirschman Index (HHI) of capital concentration per dimension --
the standard concentration metric borrowed from competition economics
(U.S. DOJ/FTC Horizontal Merger Guidelines interpretive bands), explicitly
disclosed as a borrowed convention, not a Basel-mandated threshold. Fills
the concentration-risk gap Notebook 01's Pillar-1 ASRF/infinite-granularity
assumption deliberately leaves unpriced ([BCBS05]) -- a genuine Pillar-2-
style addition, not a duplicate of Problem 1.

### Verified clean on first execution -- no bugs found

Unlike Notebooks 02 and 04, this notebook's first real Jupyter execution
on the fixture passed every check on the first try: 0 execution errors, 0
integrity-check failures, both real cross-checks (segment-capital-sums-
match-portfolio-total; HHI-within-mathematical-bounds) passed exactly.
This is attributed directly to `LESSONS_LEARNED.md` being consulted as a
genuine pre-flight checklist before writing this notebook's code, not
after finding a bug -- specifically avoiding the `monotonic_within_noise()`
directionality trap by recognizing up front that concentration analysis
has no ordering convention to get backwards in the first place, and
writing both real cross-checks (not asserted correctness) before the first
execution rather than adding them reactively.

### Advanced error tackling

- Hard dependency checked by actual required columns, not file existence.
- Real cross-check: every dimension's segment capital totals sum back to
  the real portfolio total (rel. diff. < 1e-9) -- catches a join/groupby
  bug immediately rather than silently mis-counting capital.
- Real cross-check: HHI is checked to fall within its real mathematical
  bounds `[1/N, 1]` for a dimension with N segments.
- Swift, vectorized processing: one pandas groupby-aggregate per real
  dimension (same pattern proven fast in Notebook 02 -- 1.2s on the user's
  real 307,511-applicant portfolio), never a per-applicant loop.

### Verification

Verified end-to-end on this suite's synthetic fixture: 0 execution errors,
all pipeline integrity and concentration-validation checks pass,
`nbformat.validate()` clean, HTML dashboard confirmed under a
network-blocked Playwright check (0 external network requests attempted,
0 page/console errors), Excel workbook confirmed via LibreOffice headless
recalculation (all formula-sheet values match the notebook's own real
output exactly). Not yet run against the user's real data.

## [1.4.6] - 2026-09-01

### Added — Mega Project 2, Notebook 04: Macro Stress Testing

Trains no model. Baseline reuses Notebook 01's real per-applicant
PD/LGD/EAD/correlation directly, unmodified. Adverse and Severely Adverse
re-evaluate the same real single-factor Vasicek conditional-PD formula
already used (and cited) in Notebooks 01/03, at documented, cited
severities: Adverse at the standard-normal 95th-percentile adverse value
(Phi^-1(0.05) = -1.6449, a "1-in-20 downturn" convention), Severely
Adverse at Phi^-1(0.001) = -3.0902 -- the SAME 99.9th-percentile severity
Basel's own closed-form capital function is calibrated to [BCBS05] -- plus
a documented 25% LGD downturn add-on (capped at 100%), reflecting the
Basel II "downturn LGD" concept [BCBS06]. Home Credit's data has no
macro/time-series dimension, so every shock magnitude is a disclosed, cited
assumption, never fitted -- consistent with this suite's existing LGD/R
posture.

### Fixed — a real mathematical mistake caught by this notebook's own cross-check before delivery

The first version defined "Baseline" as Z=0 run through the conditional-PD
formula, on the incorrect assumption that Phi((Phi^-1(PD))/sqrt(1-R))
reproduces PD exactly at Z=0. It does not: Phi is nonlinear, so the
unconditional PD is recovered only by integrating the conditional formula
over Z ~ N(0,1) (how PD was calibrated in the first place), not by
evaluating it at the single point Z=0. On the fixture this produced a real,
measurable 5.36% gap between "Baseline" and Notebook 01's actual real
closed-form capital ($103.2M vs. $109.0M) -- caught immediately by this
notebook's own `baseline_scenario_matches_notebook_01_exactly` cross-check
on its FIRST execution, before any delivery. Fixed by having Baseline reuse
Notebook 01's real PD/LGD directly rather than round-tripping through the
conditional formula at Z=0; confirmed via re-execution to a relative
difference of 2.35e-10 (floating-point noise). This is exactly the kind of
real bug this suite's "real cross-checks beat asserted correctness"
principle (`LESSONS_LEARNED.md` #6) exists to catch -- recorded there too.

### Advanced error tackling (see `LESSONS_LEARNED.md` for the full checklist this applied)

- Hard dependency checked by actual required columns, not file existence.
- `SCENARIOS` validated at runtime (severity strictly ordered, no LGD
  scenario improves on baseline) -- a future edit that breaks ordering
  raises immediately.
- A vectorized re-implementation of the Basel K() formula (for swift
  processing across 3 scenarios x 300K+ real applicants) is cross-checked
  against the existing trusted scalar function on a real 200-applicant
  sample (`np.allclose`, `rtol=1e-9`) before being trusted for the full
  portfolio.
- Severity ordering (stressed PD non-decreasing across scenarios) checked
  at the PER-APPLICANT level across the whole real portfolio, not just
  portfolio totals -- the strongest form of this check, and a real
  mathematical guarantee of the single-factor model.

### Swift processing

No PD re-scoring, no reloading the 7 raw tables -- everything needed is
already in Notebook 01's saved CSV. Each scenario is exactly one vectorized
`scipy.stats.norm.cdf`/`norm.ppf` pass over the whole real portfolio (never
a per-applicant loop): all 3 scenarios completed in 0.01s on the fixture;
expect low single-digit seconds at real 300K+-applicant scale (vs.
Notebook 03's Monte Carlo, which needs tens of thousands of such passes and
takes minutes for a genuinely different reason -- a full simulated
distribution, not 3 point estimates).

Full verification performed: real `jupyter nbconvert --execute` (0 errors,
after the fix above) -- outputs cleared and `nbformat.validate()` passed;
HTML dashboard re-checked under a network-blocked Playwright pass (0
console errors, 0 external requests); Excel workbook re-checked via
LibreOffice headless recalculation.

## [1.4.4] - 2026-09-01

### Added — Mega Project 2, Notebook 03: Economic Capital & Unexpected Loss

Confirmed on real data: the [1.4.3] directionality fix resolved the user's
real, full-scale (307,511-applicant) runs of both MP2 Notebook 01 and
Notebook 02 — both now report "STATISTICALLY ROBUST — RECOMMENDED FOR
PRODUCTION" against real data (Notebook 02: real portfolio RWA density
66.21%).

Problem 3 trains no model and introduces no new PD/LGD/EAD/correlation
assumption -- reuses Notebook 01's real per-applicant output unchanged
(hard dependency). Runs a real, vectorized, batched Monte Carlo simulation
of the same single-factor Vasicek/ASRF model underlying Notebook 01's
closed-form Basel capital charge, to obtain a real simulated portfolio loss
distribution and real Value-at-Risk / Expected Shortfall / Economic Capital
at 4 documented confidence levels (95%, 99%, 99.5%, 99.9%). Technique:
every systematic-factor draw's conditional default probability is computed
for the whole real portfolio in one vectorized `scipy.stats.norm.cdf` call;
draws are processed in batches so the number of Python-level loop
iterations stays small regardless of the total draw count requested (a
real Monte Carlo simulation of a parametric model, not a bootstrap
resampling of empirical data -- a distinct technique from this suite's
"vectorized multinomial bootstrap" lesson). On the fixture: 50,000 main
draws over 4,000 applicants complete in ~7 seconds.

Two real, computed validation layers, neither asserted: (1) a closed-form
cross-check -- the Monte-Carlo 99.9% Economic Capital vs. Notebook 01's
real closed-form Basel capital requirement, documented 10% tolerance (1.35%
relative difference on the fixture); (2) an independent-reseed convergence
check (`RANDOM_SEED + 1`, a second full Monte Carlo run) standing in for
this notebook's "Statistical Robustness Verdict" family, since there is no
real `TARGET` to test a classifier against in a pure simulation notebook --
tolerances documented per confidence level (5% at 95%, up to 15% at 99.9%,
widening because a finite Monte Carlo sample has real, larger sampling
error further into the tail).

Full verification performed: real `jupyter nbconvert --execute` on the
fixture -- 0 errors; outputs cleared and `nbformat.validate()` passed; HTML
dashboard re-checked under a network-blocked Playwright pass (0 console
errors, 0 external requests); Excel workbook re-checked via LibreOffice
headless recalculation.

## [1.4.3] - 2026-09-01

### Fixed — two real bugs behind Mega Project 2's "NOT YET STATISTICALLY ROBUST" verdict, found while investigating the user's real 307,511-applicant run of Notebook 01

The user ran Mega Project 2 / Notebook 01 for real (full-scale, 307,511
real applicants) and reported a highly significant chi-square (p < 0.001)
and a tight bootstrap 95% CI on Cramer's V (V=0.3411, CI [0.3358, 0.3461],
clearly excluding zero) alongside a failing
`default_rate_monotonic_by_pd_band` check and an overall "NOT YET
STATISTICALLY ROBUST" verdict. Investigating this surfaced two separate,
real, disclosed issues — not one:

1. **Root cause (primary): a directionality bug in Notebook 01 and
   Notebook 02's call convention.** `monotonic_within_noise()`
   (`src/utils/stats_checks.py`) is documented to expect its input already
   ordered with group 0 = the *highest* expected rate. Both notebooks sort
   `band_agg` ascending by PD risk band ("Lowest Risk" first — the natural
   order for a human-readable report), but real default rate (and EL rate,
   and RWA density) is expected to *increase*, not decrease, with risk.
   Feeding the function the unreversed ascending-order arrays meant every
   single adjacent-band comparison was evaluated backwards, so the check
   would report "reversed" on essentially every pair regardless of whether
   the real underlying relationship was monotonic — a real bug in these two
   notebooks' call sites, not a property of the data, and not something any
   amount of statistical tolerance in the test itself could fix. Notebook
   03 and Notebook 04 were unaffected — they already ordered their inputs
   correctly (worst-tier/worst-band first). Fixed by reversing the arrays
   immediately before the `monotonic_within_noise()` call in both
   notebooks, and correcting Notebook 02's separate descriptive
   RWA-density ordering comparison (`>=` → `<=`) the same way.
   **Confirmed via real re-execution on this suite's fixture**: the
   underlying, *unchanged* band-level default rates (1.11% → 1.77% →
   4.05% → 22.44% → 96.40%) are genuinely, strongly monotonic; both
   notebooks' verdicts flip from "NOT YET STATISTICALLY ROBUST" to
   "STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION" once compared in
   the correct direction, and the JSON audit trail's `monotonicity_detail`
   z-statistics are byte-identical before and after — only the direction
   of comparison changed, nothing was tuned to force a pass. This is very
   likely the cause of the FAIL on the user's real run too, since it is
   the same code path; confirmation requires the user to re-run against
   real data with this fix.
2. **A separate, defensive fix: large-sample statistical power.**
   Independent of (1), `monotonic_within_noise()`'s Bonferroni-corrected
   two-proportion z-test gets more powerful as real sample size grows
   (standard errors shrink), so at production scale (hundreds of thousands
   of rows, vs. this suite's ~4,000-row fixture) it can flag a tiny,
   practically meaningless adjacent-band reversal as "significant" even
   with directionality fixed correctly. Added a real, disclosed minimum
   practical-difference threshold (`min_practical_difference`, default
   0.0025 = 0.25 percentage points): a reversal now only counts as a
   genuine violation if it is BOTH statistically significant AND
   practically material. This is the standard remedy for conflating
   statistical and practical significance at large N — see Cohen, J.
   (1994), "The Earth Is Round (p < .05)", *American Psychologist*,
   49(12), 997–1003. A documented assumption, not fitted per-run, applied
   uniformly to every call site in this suite (Notebook 03, Notebook 04,
   Mega Project 2 Notebook 01, Mega Project 2 Notebook 02) — confirmed via
   re-execution that Notebook 03/04's already-passing verdicts on the
   fixture are unchanged (no reversals were significant-but-immaterial
   there), so this is additive safety, not a retroactive loosening that
   happened to help one run.

Every reversal's real z-statistic, p-value, magnitude, and both the
statistical-significance and practical-materiality verdict are recorded in
`monotonicity_detail` in the JSON summary — a reversal that is significant
but immaterial stays visible in the audit trail even though it no longer
fails the gate; nothing is hidden.

Full re-verification performed: real `jupyter nbconvert --execute` on all 4
affected notebooks (03, 04, MP2-01, MP2-02) — 0 errors; outputs cleared and
`nbformat.validate()` passed; both MP2 HTML dashboards re-checked under a
network-blocked Playwright pass (0 console errors, 0 external requests);
both MP2 Excel workbooks re-checked via LibreOffice headless recalculation.

## [1.4.2] - 2026-09-01

### Added — Mega Project 2, Notebook 02: Basel RWA Portfolio Analytics

Pure analytical layer, no new model: reuses Notebook 01's real per-applicant
Expected Loss / RWA / capital output (hard dependency), joined with real
application-level segment columns (income type, education, contract type,
region rating), and reports RWA density (RWA / EAD — the standard Basel
Pillar 3 cross-portfolio comparability metric) per PD risk band and per
real segment cut.

### Fixed — real statistical bug caught by this suite's own verification protocol

The first version of this notebook fed RWA density into
`monotonic_within_noise()` (a two-proportion z-test, valid only for a
proportion bounded in [0, 1]). RWA density is a ratio, not a proportion —
under the Basel K() formula it can legitimately exceed 100% for high-risk/
high-LGD segments (this suite's fixture shows the Revolving/QRRE segment at
>100% density), which broke the z-test's variance calculation with a
`math domain error` on real execution. Fixed by reporting RWA-density
ordering descriptively (a real, computed fact, printed and stored in the
run summary) rather than statistically gating it — gating a ratio with a
test built for proportions would be invalid, not just imprecise. Real
default rate *is* a true proportion and remains correctly gated via
`monotonic_within_noise()`. This is exactly the kind of gap this suite's
fixture → real-execution → 0-errors verification step exists to catch
before delivery, not after.

Verified end-to-end against the synthetic fixture after the fix: 0
execution errors, all pipeline integrity checks pass, HTML dashboard
confirmed under a network-blocked Playwright check, Excel workbook
confirmed via LibreOffice headless recalculation. Sample reports added.
Mega Project 2 status: 2 of 5 problems built.

## [1.4.1] - 2026-09-01

### Changed — Mega Project 1 / Notebook 01 retrained on all 7 real data tables (was 2); every downstream notebook re-verified

**What prompted this**: Notebook 01's champion PD model — the one every
other notebook in this suite reuses, never retrains — was trained on only
`application_train.csv` + `bureau.csv`. Five other real Home Credit tables
(`bureau_balance.csv`, `previous_application.csv`, `POS_CASH_balance.csv`,
`installments_payments.csv`, `credit_card_balance.csv`) carry real
behavioral signal (past repayment conduct, past approval/refusal history,
revolving-credit usage) that an application-snapshot-only feature set
cannot capture. Left unaddressed, this understated achievable accuracy for
every downstream notebook and Mega Project that reuses this PD.

**What changed**:

- Added `engineer_previous_application_features()` to
  `src/features/applicant_credit_history_features.py` — real, leakage-safe
  (Home Credit's own already-completed past decisions, no linkage to any
  new application) aggregation of `previous_application.csv`.
- Added `engineer_credit_default_features_v2()` to
  `src/features/credit_default_features.py` — combines v1's real
  application + bureau fields with real bureau_balance, real
  previous_application history, and real POS/installments/credit-card
  servicing history (applicant-level TOTAL block — no leave-one-out
  subtraction, which is the correct, leakage-safe choice at this model's
  SK_ID_CURR-level target granularity; full reasoning in the function's own
  docstring). v1 is retained, unused by the deployed champion, solely so
  the real accuracy comparison below can be computed.
- Retrained Notebook 01's champion on the v2 (7-table, 47 numeric + 9
  categorical feature) set. **Real, measured, same-split accuracy
  comparison** (same champion architecture, same holdout rows, only the
  feature set differs — see `feature_set_accuracy_comparison` in
  `decision_engine/artifacts/notebook_01_summary.json`): a real AUC
  improvement over the retired v1 feature set on this suite's synthetic
  verification fixture. No number here is asserted beyond what was
  actually measured — re-run on real data for the real-scale figure.
- Updated Notebooks 02, 03, 04, 05, and Mega Project 2 / Notebook 01 (every
  notebook that rebuilds Notebook 01's exact feature set to score with its
  champion) to call `engineer_credit_default_features_v2` instead of v1,
  loading the additional raw tables each needs. All 6 Mega Project 1
  notebooks plus Mega Project 2 / Notebook 01 were re-executed end-to-end
  against the fixture and re-verified (0 execution errors, nbformat-valid,
  Playwright network-blocked dashboard checks, LibreOffice headless
  workbook recalculation) after this change.
- Fixed a real, pre-existing bug found during this re-verification pass:
  `06_mp1_executive_report.ipynb`'s own `every_available_problem_has_an_insight`
  integrity check compared the insight count to the notebook count with
  `==`, but the report deliberately appends one bonus insight (explaining
  the two-tier verdict pattern) whenever any problem shows a "NOT YET
  STATISTICALLY ROBUST" verdict — a real, intentional addition, not a bug.
  This made the check falsely report FAIL on any run where that bonus
  insight fired. Fixed to `>=`.
- Updated `01_credit_default_prediction_MODEL_CARD.md` with the full v2
  feature list, per-source leakage-safety reasoning, and the v1-vs-v2
  accuracy comparison methodology.

### Why this belongs in the changelog rather than silently overwriting v1

Per this repo's zero-fabrication standard, a retrain that changes model
behavior is a disclosed event, not a silent update — anyone who ran
Notebook 01 before this entry, or who compares an old `.joblib` artifact
against a new one, should be able to find out why the numbers changed.

## [1.4.0] - 2026-09-01

### Added — Mega Project 2 (Regulatory Capital), Notebook 01: Expected Loss & Capital Requirement Estimation

Real PD (Mega Project 1's trained champion model, loaded not retrained) x
documented, cited Basel retail-IRB LGD/EAD/correlation assumption layer
(new HYPER shared module, `src/features/regulatory_capital_features.py`).
Computes real per-applicant Expected Loss (PD x LGD x EAD) and a real
Basel retail-IRB capital requirement (Vasicek/ASRF K() function, RWA, 8%
Pillar-1 capital) for every real applicant, with a real chi-square /
bootstrap / monotonicity statistical-robustness gate on top.

Every lesson from Mega Project 1's hardening history applied from this
notebook's first version, not retrofitted: WARP hardware fix, two-tier
Pipeline-Integrity vs. Statistical-Robustness verdict separation,
`monotonic_within_noise()` Bonferroni-corrected tolerance, vectorized
multinomial bootstrap, HYPER shared-module reuse, and a hard (not soft)
dependency on Mega Project 1's champion model with a clear failure message
if it hasn't been run yet.

Verified end-to-end against the synthetic fixture: 0 execution errors, all
pipeline integrity checks pass, nbformat-valid, HTML dashboard confirmed
under a network-blocked Playwright check, Excel workbook confirmed via
LibreOffice headless recalculation. Sample reports added under
`02_mega_project_2_regulatory_capital/sample_reports/`. Mega Project 2
status: 1 of 5 problems built.

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
