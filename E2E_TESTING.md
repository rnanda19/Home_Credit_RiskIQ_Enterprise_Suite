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

Three real end-to-end test files built on it, each hitting a real running
subprocess over real HTTP via `requests` (not `TestClient`):

- `01_mega_project_1_underwriting_approval/tests/test_e2e_live_service.py`
  — MP1 Problem 1's `credit_default_scoring_service.py` (a
  `scoring_service_common`-built classifier service). Exercises: `/health`
  open with no auth, `/schema`/`/score` correctly reject missing auth, a
  real `POST /token` OAuth2 exchange followed by a real Bearer-authenticated
  `/schema` call, a real `X-API-Key`-authenticated `/score` call, and a real
  `/adverse-action-notice` call — end to end, through a real process, for
  every hardening feature added this session.
- `03_mega_project_3_risk_segmentation/tests/test_e2e_live_service.py` —
  MP3 Problem 2's `bureau_segment_assignment_service.py` (a
  `segment_assignment_common`-built **clustering** service — a genuinely
  different app shape from MP1's classifier). Proves the harness is a real,
  generalized component, not hardcoded to one service's shape.
- `05_mega_project_5_liquidity_cashflow/tests/test_e2e_live_service.py` —
  MP5 Problem 4's `prepayment_segment_assignment_service.py`, the third
  Mega Project and third real service now covered by this harness.

Both tests use the exact same synthetic fixture bundle
`scripts/generate_ci_fixture_bundles.py` already uses to verify this
suite's Docker images build and run in CI (`scoring_bundle()` /
`segment_bundle()`, imported directly, not duplicated) — so this test needs
no real Kaggle data and no locally-run notebook, and reuses real,
already-audited fixture logic rather than inventing new fake data.

Wired into CI for free: `.github/workflows/ci.yml`'s existing `unit-tests`
matrix job already runs `pytest tests/ -v` inside each Mega Project
directory, so it picks these two files up automatically — the only change
needed was adding `requests` to that job's install line.

## Real, disclosed scope limits

- Three services out of 15 are covered this way (one classifier, two
  clustering — the two real app shapes this suite's shared serving
  factories produce). The other 12 remain covered by `TestClient`-based
  tests only. Extending to another service means copying any existing test
  file's shape and pointing it at that service's module name, port, and
  bundle-path env var — the harness itself needs no changes.
- This proves the real process *starts* and *serves real traffic
  correctly* — it does not additionally re-prove rate-limiting behavior
  under load (see `src/tests/test_rate_limit_common.py`'s real end-to-end
  429 proof) or real concurrent-load latency (see `LOAD_TESTING.md`'s real
  Locust run) — those are already covered elsewhere and are not duplicated
  here.
- Each test spins up and tears down a real subprocess per test function
  (via a pytest fixture), which is why this suite is small (8 tests total)
  rather than exhaustive — subprocess startup has real, measurable
  overhead (each MP1 test run: 2-5 real seconds of `uvicorn` startup).
