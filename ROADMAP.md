# Roadmap

Forward-looking status and next steps for the suite. For the full,
itemized, version-by-version history of every real fix, rename, and
scope change already made, see [`CHANGELOG.md`](CHANGELOG.md) — this
file is the summary and what's-next view; `CHANGELOG.md` is the
detailed record.

## Mega Project status

| # | Mega Project | Notebooks | Recommended | Services | Docker | Tests | Sample reports | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | Underwriting & Approval Intelligence | 6/6 | 5/5 | 4 | ✅ | ✅ | removed 2026-09-02 (see live dashboards) | **Built & hardened** |
| 2 | Regulatory Capital & Stress Testing | 6/6 | 5/5 | 2 | ✅ | ✅ | removed 2026-09-02 (see live dashboards) | **Built & hardened** |
| 3 | Risk Segmentation | 6/6 | 4/5 (Problem 3: NOT YET STATISTICALLY ROBUST) | 4 | ✅ | ✅ | removed 2026-09-02 (see live dashboards) | **Built & hardened** |
| 4 | Delinquency Prevention | 6/6 | 5/5 | 4 | ✅ | ✅ | removed 2026-09-02 (see live dashboards) | **Built & hardened** |
| 5 | Liquidity & Cashflow | 6/6 | 5/5 | 1 (verified against a real trained bundle) | ✅ | ✅ | removed 2026-09-02 (see live dashboards) | **Built & hardened** |

**Suite total: 24 of 25 real problems statistically robust and
recommended for production**, per your own real, current
`00_suite_executive_summary.json`. The 1 disclosed exception is Mega
Project 3's Problem 3 (Repayment Behavior Segmentation), which fails the
`cramers_v_ci_excludes_zero` significance gate on your real data — a
separate, stricter check from the structural pipeline-integrity checks it
does pass. See that problem's own `MODEL_CARD.md` for the full detail.

Each built Mega Project's own `README.md` and `CHANGELOG.md` (in its
own folder) carry the problem-by-problem detail; this table is the
suite-wide summary.

## Hardening track — status

All 5 Mega Projects are now at full parity on:

- Real notebooks, verified end-to-end (execute → 0 errors → clear
  outputs → `nbformat` validate → Playwright network-blocked dashboard
  check → LibreOffice headless workbook recalc check) — **except Mega
  Project 4's Problems 3-6**, which per an explicit 2026-09-01 policy
  change were instead verified with small, hand-built test cases plus a
  syntax/AST check and `nbformat.validate()`, with no fixture execution;
  see that Mega Project's own README for the full disclosure. All
  `sample_reports/` fixture-era folders (Mega Projects 1-4) were removed
  2026-09-02 — superseded by the real GitHub Pages live dashboards.
- Deployable FastAPI services for every problem where a per-record
  service is a meaningful thing to build (population-level analyses
  deliberately have none — see each Mega Project's own README for the
  disclosed scope boundary), with Docker Compose orchestration and a
  pytest suite verifying each service bit-identical against an
  independent reference computation. 15 services total across the suite
  (14 across Mega Projects 1-4, plus Mega Project 5's Problem 4 service).
- CI (`ci.yml` notebook-syntax + unit-tests, `code-quality.yml`
  pyflakes/black/bandit) running across all 5 Mega Projects.
- GitHub Pages live dashboards for all 3 of Mega Projects 1-3's problems,
  plus Mega Project 4's Problems 1-2 (the only ones with a fixture-
  generated dashboard to publish).
- An architecture flow diagram (Mermaid + PNG) embedded directly in each
  Mega Project's own `README.md`.
- **Real `X-API-Key` authentication on every `/schema` and `/score`
  endpoint of all 15 deployable services** (`/health` stays open, for
  liveness probes), plus real per-request explainability
  (`"top_reasons"` on every classifier-backed service,
  `"distance_to_each_segment"` on every clustering-backed one). Retrofit
  onto the 10 pre-existing Mega Project 1-3 services in [1.9.7]; built in
  from day one for Mega Project 4's 4 new services in [1.9.8] — closing
  this suite's own version of the exact gap the AMEX RiskIQ Enterprise
  Credit Risk Platform's own hardening history documents having found and
  fixed in itself. See `CHANGELOG.md` [1.9.7]/[1.9.8] for the full detail.

Mega Project 5 is built (6/6 notebooks), verified end-to-end, and fully
hardened — all 5 problems recommended for production. Its Problem 4
service (`services/prepayment_segment_assignment_service.py`) is now
verified against a real, fitted `.joblib` bundle three independent ways:
the existing unit test comparing the service's output to Notebook 04's
own real segment assignment, a real live-subprocess + real-HTTP check,
and a permanent CI-safe end-to-end test
(`tests/test_e2e_live_service.py`). The executive rollup notebook
(Notebook 06) now also carries a real, filesystem-checked "Service
Status" column so this stays truthful automatically on every future
rerun, rather than being a claim someone has to remember to update. See
its own `README.md`/`CHANGELOG.md` for current status.

## What's not yet done

- **Kaggle packaging is live but not yet reflected in this repo.** All 5
  Mega Projects have real, execution-verified showcase notebooks pushed
  to Kaggle (private, under account `rnanda1976`), mirroring the AMEX
  repo's Kaggle presence. The submission notebooks and
  `kernel-metadata.json` files for that push currently live outside this
  repo (`Downloads\kaggle-submissions\`) and the kernels themselves
  aren't linked from this repo's README yet — bringing those into this
  repo (or at minimum linking the 5 kernel URLs from the root README) is
  the one remaining packaging step.

## Fixed since the above was written (2026-09-08)

- **Repo-wide `black` reformat**: done. All 38 files `black --check` used
  to flag are reformatted (pure style, zero logic change -- every existing
  test suite re-verified passing afterward). CI's lint gate
  (`.github/workflows/code-quality.yml`) is now blocking, not advisory --
  the `|| true` fallback on both `pyflakes` and `black --check` is gone.
- **Verified container build & run**: done, for real, in CI --
  `.github/workflows/docker-build-verify.yml` builds and runs all 5 Mega
  Projects' Docker images on GitHub Actions' own `ubuntu-latest` runners
  (Docker ships preinstalled there) and curls each one's real `/health`
  endpoint inside the running container. This build environment still has
  no local Docker daemon, so local verification remains structural only --
  but the actual `docker build && docker run` this file used to say had
  never been performed now runs on every push, using synthetic fixture
  model bundles (`scripts/generate_ci_fixture_bundles.py` -- proves the
  image builds and the service starts, proves nothing about model
  quality, which is validated separately at the notebook level on the
  real dataset).
- **File-based model registry**: done -- see `MODEL_REGISTRY.md`.
- **Data privacy/PII documentation**: done -- see `DATA_PRIVACY.md`.
- **OAuth2/JWT authentication**: done -- every service now accepts a real
  OAuth2/JWT Bearer token (issued by its own `POST /token`, HS256-signed,
  scoped, real expiry) as an alternative to the existing `X-API-Key`
  header, via `serving.auth_common.require_auth`. The static API key is
  kept as a documented secondary path for simple machine-to-machine batch
  callers, not removed -- see `README.md`/`CHANGELOG.md` [2.1.3].
- **MP2 Docker image bug found and fixed by the new Docker verification
  job, on its very first real run**: `02_mega_project_2_regulatory_capital/docker/Dockerfile`
  was missing `COPY src/serving /app/src/serving`, so its container
  crashed on import at startup and never served `/health` -- invisible
  until a real `docker build`/`docker run` was performed against it for
  the first time. Fixed; all 5 Mega Projects now build, run, and pass
  their `/health` check in CI.
- **Production drift monitoring**: done for one flagship model -- see
  `MONITORING.md` for the real job, the real baseline generator, and the
  honest scope of what's covered so far (Mega Project 1 Problem 1 only;
  extending to the other 24 problems is unstarted, same shape of gap the
  AMEX platform discloses for its own monitoring job).
- **Real API hardening -- rate limiting + TLS termination**: done.
  `src/serving/rate_limit_common.py` adds real, tested, per-process
  slowapi rate limiting to every `/token`, `/schema`, `/score` (and MP2's
  `/score/{scenario}`) route across all 20 services (both shared
  factories + all 5 standalone services) -- 6 new tests, including a real
  end-to-end proof against the real scoring-service factory (60 real
  calls succeed, the 61st gets a real 429). TLS termination is verified
  end-to-end in CI (`tls-termination-verify` job) for one flagship
  service -- a real self-signed cert, a real nginx TLS listener, a real
  HTTPS request reaching the real running service -- see `TLS.md` for the
  honest scope (one service demonstrated, not yet wired into
  `docker-compose.yml` for local/production use).
- **Real load testing**: done for one flagship service (MP1 Problem 1) --
  see `LOAD_TESTING.md`. A real Locust load test
  (`01_mega_project_1_underwriting_approval/loadtest/locustfile.py`) run
  against a real live instance of the real service surfaced a real,
  interesting finding: the rate limiter added above correctly rejects
  requests past 60/minute even under real concurrent load (677 of 737
  `/score` calls got a real `429` in one real run), with real measured
  latency for the accepted requests (median 5ms, p99 110ms). Honest scope
  in `LOAD_TESTING.md`: one service, synthetic local load from one
  machine, not genuine unpredictable production traffic.
- **Real ECOA/Reg B adverse-action notices**: done -- see
  `ADVERSE_ACTION.md`. `src/serving/adverse_action_common.py` turns this
  suite's existing real explainability output into plain-English,
  ECOA/Reg B-style "specific reasons," with sex/marital-status/age and two
  real fair-lending-proxy features (social-circle default history, coarse
  geography) structurally removed from the customer-facing reason list at
  generation time, not just documented as a risk. Wired into every
  factory-built classifier service via `build_scoring_app()`'s new
  `POST /adverse-action-notice` endpoint (HYPER). 13 new tests, full suite
  65/65 passing. Does not audit the underlying model for disparate impact
  -- that remains the separate, permanently-open fair-lending/bias-audit
  gap.
- **Real end-to-end integration testing**: done -- see `E2E_TESTING.md`.
  `src/testing/e2e_process_harness.py` launches a real service as a real
  `uvicorn` subprocess and talks to it over real HTTP (`requests`, a real
  socket), closing the gap that every prior service test used in-process
  `TestClient` only. Three real end-to-end test files now exist (MP1's
  classifier service, MP3's clustering service, and MP5's Problem 4
  service -- deliberately different app shapes), wired into the existing
  CI matrix job for free. 3 of 15 services covered this way; the other 12
  remain `TestClient`-only.
- **Mega Project 5, Problem 4 — real trained bundle produced and its
  service verified end-to-end**: done. Notebook 04 was re-run on the
  real, full-scale Home Credit dataset and now produces a real fitted
  clustering bundle (real k=3 KMeans, real fitted StandardScaler over 8
  real features). The deployable service is verified against that real
  bundle, and the executive rollup (Notebook 06) now reports a real,
  filesystem-checked Service Status per problem instead of a static
  claim. This closed the suite's last remaining disclosed "service
  unverified against real data" gap.

## Immediate next steps (in order)

1. Bring the Kaggle packaging into this repo: either commit the 5
   submission notebooks + `kernel-metadata.json` files here, or at
   minimum link the 5 live kernel URLs from the root README, so the
   Kaggle presence is discoverable from GitHub rather than only known
   separately.
2. Repo hygiene: relocate the remaining root-level utility scripts into
   `scripts/`, and clear the outstanding Dependabot version-bump PRs.
3. If further hardening is wanted beyond what's disclosed as
   intentionally partial scope: extend drift monitoring past Mega
   Project 1 Problem 1, and extend real end-to-end integration testing
   past the 3 services that currently have it. Neither is required for
   any problem's own production-readiness verdict — both are scope
   extensions, not open defects.
