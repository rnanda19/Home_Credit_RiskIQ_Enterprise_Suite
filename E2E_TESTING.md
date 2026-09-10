# End-to-End Integration Testing

This document exists to close a real, previously-disclosed gap: "No
end-to-end integration test suite exists — every existing service test
uses in-process `TestClient`, which never exercises the real `uvicorn`
startup path, real networking, or real process lifecycle."

## What existed before, and why it wasn't enough

Every service test in this suite (`tests/test_scoring_services.py` in each
Mega Project, `src/tests/test_rate_limit_common.py`,
`src/tests/test_adverse_action_endpoint.py`) uses FastAPI's `TestClient`,
which calls the ASGI app directly, in-process, in-memory — no real TCP
socket, no real `uvicorn` process, no real serialization round trip. These
tests are genuinely valuable (fast, precise, bit-identical-output
verification against an independent reference computation) and are **not
replaced** by anything below — they remain the right tool for "does this
service compute the right answer."

What they cannot tell you: whether the service actually *starts* the way
`README.md` documents (`uvicorn <module>:app --host 0.0.0.0 --port <N>`),
the same way this suite's own Dockerfiles start it in a real container.

## What exists now

`src/testing/e2e_process_harness.py` — a HYPER shared component,
`run_service_subprocess()`, that launches a real service as a real OS
subprocess, polls its real `/health` endpoint over real HTTP until it
answers, yields the running service's real base URL, and guarantees real
process teardown afterward (including on a failing test). On a startup
failure it raises with the real captured subprocess stdout/stderr attached
— a bare timeout with no diagnosis was the wrong failure mode for a test
whose whole point is closing a "harder to debug" gap.

Five real end-to-end test files built on it, one per Mega Project, together
covering all 15 of the suite's deployable services — each hitting a real
running subprocess over real HTTP via `requests` (not `TestClient`):

- `01_mega_project_1_underwriting_approval/tests/test_e2e_live_service.py`
  — all 4 MP1 services (Problem 1 added 2026-09-08; Problems 2/3/4 added
  2026-09-10). Covers both real app shapes this Mega Project ships: 3
  `scoring_service_common`-built classifier services and 1 hand-built,
  no-model deterministic-formula service (Problem 4). Exercises: `/health`
  open with no auth, `/schema`/`/score` correctly reject missing auth, a
  real `POST /token` OAuth2 exchange followed by a real Bearer-authenticated
  `/schema` call, real `X-API-Key`-authenticated `/score` calls, and real
  `/adverse-action-notice` calls where the service exposes one — 16 tests.
- `02_mega_project_2_regulatory_capital/tests/test_e2e_live_service.py` —
  both MP2 services (added 2026-09-10). Neither needs a model bundle at all
  (real, closed-form Basel Vasicek/ASRF formulas) — every expected numeric
  value in this file was independently hand-recomputed via `scipy.stats.norm`
  against the exact same formula before being written into the test, not
  copied from a live response — 9 tests.
- `03_mega_project_3_risk_segmentation/tests/test_e2e_live_service.py` —
  all 4 MP3 services (Problem 2 added 2026-09-08; Problems 1/3/4 added
  2026-09-10). Covers a third real app shape: a hand-built,
  deterministic-lookup service with no trained model (Problem 1's risk-tier
  assignment), alongside three `segment_assignment_common`-built clustering
  services — 14 tests.
- `04_mega_project_4_delinquency_prevention/tests/test_e2e_live_service.py`
  — all 4 MP4 services (added 2026-09-10, this Mega Project's first E2E
  coverage of any kind) — 14 tests.
- `05_mega_project_5_liquidity_cashflow/tests/test_e2e_live_service.py` —
  MP5 Problem 4's `prepayment_segment_assignment_service.py` (added
  2026-09-08, verified against a real trained bundle 2026-09-08) — 3 tests.

**56 real end-to-end tests total, across all 15 deployable services.**

Every test uses the exact same synthetic fixture bundles
`scripts/generate_ci_fixture_bundles.py` already uses to verify this
suite's Docker images build and run in CI (`scoring_bundle()` /
`segment_bundle()`, imported directly, never duplicated) — so none of these
tests need real Kaggle data or a locally-run notebook, and all of them
reuse real, already-audited fixture logic rather than inventing new fake
data per file.

Wired into CI for free: `.github/workflows/ci.yml`'s existing `unit-tests`
matrix job already runs `pytest tests/ -v` inside each Mega Project
directory, so it picks up every one of these five files automatically —
no CI configuration change was needed to add Mega Projects 2 and 4's new
files, or Mega Projects 1 and 3's new tests within their existing files.

## Real, disclosed scope limits

- All 15 deployable services are now covered this way — this is not a
  partial rollout. What it does NOT additionally re-prove: rate-limiting
  behavior under load (see `src/tests/test_rate_limit_common.py`'s real
  end-to-end 429 proof) or real concurrent-load latency (see
  `LOAD_TESTING.md`'s real Locust run, currently one flagship service only)
  — those are separate, disclosed scope boundaries, not gaps in this file.
- Each test spins up and tears down a real subprocess per test function
  (via a pytest fixture) — real, measurable overhead per test (roughly
  2-5 real seconds of `uvicorn` startup each), which is why the full
  56-test suite takes low single-digit minutes to run, not seconds.
