# Baseline Validation Report — Home_Credit_RiskIQ_Enterprise_Suite

**Audited:** 2026-10-14 · **Commit audited:** `5f89bb63` ("Add system architecture diagram to README introduction") · **Branch:** `main`
**Method:** Independent, hands-on verification against the local clone — not a re-read of README claims. Every number below came from a command actually run during this audit (pytest, grep, git, file inspection), not from documentation.

This report follows one rule throughout: a README claim, a green CI badge, or a committed report file is a *claim*, not *proof*. Proof is a test that was actually executed, a file that was actually inspected, or a scan that was actually run. Findings are grouped by capability, each tagged:

- ✅ **VERIFIED** — independently reproduced, right now, with evidence shown.
- ⚠️ **PARTIAL** — real and working, but narrower in scope than a casual read of the docs might suggest.
- 🔧 **GAP** — a real, concrete issue worth fixing.

---

## 1. Test suites — ✅ VERIFIED (real, independently re-run)

Every number below is from `python3 -m pytest` executed against this exact clone during this audit, not copied from a prior CI log.

| Suite | Result | Notes |
|---|---|---|
| `src/tests/` (HYPER shared-component tests) | **65 passed**, 0 skipped, 0 failed (14.2s) | auth, rate-limiting, adverse-action, monitoring-job tests |
| `01_mega_project_1/tests/` | **26 passed**, 0 skipped (34.0s) | real `.joblib` bundles present locally → bit-identical assertions actually ran, not skipped |
| `02_mega_project_2/tests/` | **15 passed**, 0 skipped (13.3s) | closed-form Basel calc, no model bundle needed |
| `03_mega_project_3/tests/` | **15 passed**, 3 skipped (22.5s) | skip reason is explicit and honest: *"Notebook 0N has not been run yet, or raw fixture CSVs are not present locally"* — not a silent/misleading skip |
| `04_mega_project_4/tests/` | **18 passed**, 0 skipped (30.1s) | |
| `05_mega_project_5/tests/` | **4 passed**, 0 skipped (8.1s) | |
| **Total** | **143 passed, 3 skipped, 0 failed** | |

**Important nuance found, not assumed:** `requirements-services.txt` contains a self-documented 2026-09-05 note explaining that CI's `unit-tests` job runs on a *fresh clone with no model bundle present*, so `test_scoring_services.py`'s skip-if-missing guards skip the real assertions entirely in CI. In other words: **a green CI badge on this repo does not by itself prove the scoring services work against a real trained model** — that only gets proven once someone (like this audit) runs the notebooks or already has bundles on disk. This audit happened to find 10 real `.joblib` bundles already present locally (MP1: 2, MP3: 3, MP4: 4, MP5: 1 — none for MP2, which needs none), which is why the MP1/4/5 numbers above are real, non-skipped, bundle-backed assertions rather than CI's skipped version.

---

## 2. Notebooks — ⚠️ PARTIAL (real pipeline, but outputs are cleared before commit)

- **31 tracked notebooks** confirmed via `git ls-files` (30 per-MP notebooks [5 MPs × (5 problems + 1 rollup)] + 1 suite-level `00_suite_executive_rollup.ipynb` — consistent with the README's "30" figure, which scopes to the per-MP count only).
- Only **2 of 31** notebooks have any cell with a saved `execution_count` (i.e., visible proof-of-run in the committed file itself). The other 29 have been cleared before commit — a common, defensible practice (clean diffs, smaller repo), but it means **the notebooks themselves are not self-evident proof of execution**. The real evidence has to come from elsewhere: the 10 real `.joblib` bundles found on disk, and the DOCX/XLSX reports under `decision_engine/reports/` that `.gitignore` explicitly keeps as committed deliverables.
- Full re-execution of all 31 notebooks against the real 307K-row Kaggle tables was **not attempted in this audit** — each notebook runs long enough, and this session's tool calls are capped at 180 seconds each, that a full suite-wide rerun needs to happen outside this audit (realistically, on your own machine, same as you've already been doing).

---

## 3. CI/CD — ✅ VERIFIED, with one naming correction

Four real workflow files exist (`.github/workflows/`): `ci.yml`, `docker-build-verify.yml`, `code-quality.yml`, `codeql.yml`. Dependabot is configured (`.github/dependabot.yml`).

| Capability | Real? | Where |
|---|---|---|
| Notebook syntax validation | ✅ | `ci.yml` → `notebook-syntax` job |
| Shared-component tests | ✅ | `ci.yml` → `shared-tests` job |
| Unit tests + real E2E harness | ✅ | `ci.yml` → `unit-tests` job, references `tests/test_e2e_live_service.py` + `src/testing/e2e_process_harness.py` |
| Docker build & run verification | ✅ | `docker-build-verify.yml` → `docker-build-verify` job |
| nginx TLS termination verification | ✅ | `docker-build-verify.yml` → `tls-termination-verify` job |
| Lint | ✅ | `code-quality.yml` → `lint` job |
| SAST security scan | ✅ | `code-quality.yml` → `security-scan` job, runs `bandit` (pinned 1.9.4), blocking, against `src/`, all 5 `services/` dirs, and `demo/` |
| CodeQL | ✅ | `codeql.yml` |

**Correction to the diagram I built earlier this session:** I had labeled two of these as if they were their own workflow *files* — `tls-termination-verify.yml` and `e2e-tests.yml`. They're real, but they're **jobs inside `docker-build-verify.yml` and `ci.yml` respectively**, not separate files. The capability is genuine; only the diagram's file-level granularity was wrong. Worth a quick fix next time the diagram is touched.

---

## 4. Docker & deployment — ✅ VERIFIED

Checked all 5 `*/docker/Dockerfile` directly:

- **Non-root user:** all 5 contain `USER appuser`.
- **Real HEALTHCHECK:** all 5 contain a Docker-native `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3` hitting each service's real `/health` endpoint — not just a docker-compose-level check.
- **nginx TLS termination:** 5 `nginx.conf` files exist (one per Mega Project), matching the README's claim.

---

## 5. API authentication — ✅ VERIFIED, 15/15, via shared factories (good architecture)

All **15** deployable service files were enumerated and checked individually (not sampled). Every one gets real authentication through one of two shared factory functions rather than duplicating auth logic per service:

- `serving/scoring_service_common.py` → `build_scoring_app()` — used by the scoring-style services
- `serving/segment_assignment_common.py` → `build_segment_app()` — used by the segment-assignment-style services

Both factories import `serving.auth_common.{require_auth, add_token_route}` and wire `Depends(require_auth)` onto every `/schema`, `/score`, and (where present) `/adverse-action-notice` route, plus a real `POST /token` OAuth2 endpoint. This is a stronger pattern than per-file auth code: one place to audit, one place to harden, no risk of a 16th service someday forgetting to add auth.

---

## 6. Monitoring — ✅ VERIFIED (real code, not just `MONITORING.md`)

Real implementation exists, not only documentation: `src/monitoring/monitoring_common.py`, `src/monitoring/monitoring_job.py`, `scripts/generate_monitoring_baseline.py`. (`.gitignore` correctly keeps `*_baseline.json` and `*_job_log.csv` out of the repo, since those are derived from real training data / real run history — appropriate for a public repo.)

---

## 7. Load testing — ⚠️ PARTIAL, and already honestly disclosed as such

`LOAD_TESTING.md` itself states its own scope plainly — it does **not** overclaim: *"This document exists to close a real, previously-disclosed gap... `01_mega_project_1.../loadtest/locustfile.py` — a real Locust load test against MP1 Problem 1's real service."* A real run's real latency/throughput numbers (2026-09-08) are included. README.md does not mention load testing at all, so there's no README/reality mismatch here.

The gap, stated plainly: load testing exists for **1 of 15 services** (MP1 Problem 1 only). MP2–MP5 have no `loadtest/` directory. This is a legitimate Phase-2 candidate, not a documentation problem.

---

## 8. Dependency pinning & security — 🔧 GAP (the most concrete finding in this audit)

- `requirements.txt` and every `requirements-services.txt` use **`>=` minimum-version constraints only** — zero exact (`==`) pins anywhere.
- **This is not theoretical.** Running the real test suite (section 1) against this exact clone produced repeated `sklearn.exceptions.InconsistentVersionWarning: Trying to unpickle estimator ... from version 1.9.0 when using version 1.7.2` — the `.joblib` bundles on disk were trained with scikit-learn 1.9.0; the environment's loose `scikit-learn>=1.4` constraint installed 1.7.2 instead. Tests still passed here, but an unpinned, meaningfully-older minor version loading a newer version's pickle is exactly the kind of drift that can silently change behavior — scikit-learn's own warning says so.
- **`python-jose[cryptography]>=3.5.0`** (used for the real OAuth2/JWT implementation in `auth_common.py`) — a `pip-audit` scan flagged **CVE-2026-85394** against version 3.5.0 specifically. Because the constraint is `>=3.5.0` rather than a higher minimum or an exact pin, a fresh install can still land on the vulnerable version.
- **Positive finding:** `bandit` SAST scanning is real and blocking in CI (section 3), and Dependabot is configured — the gap is specifically *dependency-vulnerability* scanning and *version pinning*, not security tooling in general.
- **Methodology caveat:** `pip-audit` could only be run against this session's whole device Python environment (a clean per-project virtualenv failed to create — disk space), so most of its output is noise from unrelated system packages (`ufw`, `distro-info`, etc.) that aren't part of this project. `python-jose` is the one finding directly tied to a real project dependency and worth treating as real.

---

## 9. Secrets exposure — ✅ VERIFIED clean

`git grep` across all tracked `.py`/`.yml`/`.yaml`/`.json` files for secret-shaped assignments found exactly two matches, both in `src/serving/auth_common.py`, both clearly self-labeled dev placeholders:
```
DEV_DEFAULT_API_KEY = "dev-only-CHANGE-ME-before-deploying"
DEV_DEFAULT_JWT_SECRET = "dev-only-jwt-secret-CHANGE-ME-before-deploying"
```
No real credentials, keys, or tokens found committed anywhere in the tracked tree.

---

## 10. Repo hygiene — 🔧 GAP (low risk, high visibility to a reviewer)

- **6 scratch commit-message files are tracked at the repo root**: `commit_msg7.txt`, `commit_msg9.txt` through `commit_msg13.txt`. These are clearly leftover working files (not referenced anywhere), and they're the first thing a reviewer sees when browsing the repo root on GitHub.
- An **empty `tests/` directory** sits at the repo root (zero files, not even a `.gitkeep` or a README explaining it defers to `src/tests/` and the per-Mega-Project `tests/` dirs) — confusing for a reviewer who expects it to hold something.
- (Checked and confirmed clean: `_to_delete/` and `all ipynb and py files/` exist only locally on this machine and are correctly excluded by `.gitignore` — they are **not** committed, so they aren't a public-facing issue.)

---

## 11. Cross-document consistency — ✅ spot-checked, no contradiction found

- MP1 Problem 1's model card (`01_credit_default_prediction_MODEL_CARD.md`) deliberately avoids hardcoding a static AUC figure — it states *"actual AUC are determined by your real data when you run the notebook"* — which structurally prevents the stale-number-vs-dashboard contradiction this audit was looking for.
- Git history shows a dedicated commit from 2026-09-10 ("Full recruiter-readiness pass: fix cross-file contradictions and stale figures") that already resolved several real contradictions between model cards, the Status section, and ROADMAP.md. A full line-by-line re-check of all 25 problems' model cards against their dashboards was not performed in this pass (time-boxed); the sample checked was consistent.

---

## Overall picture

This is a genuinely more rigorously built repo than the audit assumed going in. The things that sound like marketing claims — non-root containers, real health checks, 15/15 services authenticated, bandit SAST in CI, honest skip-if-missing test guards, a load-testing doc that scopes itself honestly instead of overclaiming — mostly turned out to be real, and were independently reproduced here, not just re-read. The concrete, worth-fixing items are narrower than "audit the whole system" might imply: dependency pinning (with a real, observed version-drift incident as evidence), one specific CVE-affected minimum version, six stray files at the repo root, and a documentation/diagram correction for two CI job names.

## Suggested Phase 2 priorities (not yet implemented — for your review before I touch anything)

1. **Pin dependencies** — move `requirements.txt` / `requirements-services.txt` from `>=` to `==` (or at minimum add upper bounds), and re-generate the `.joblib` bundles under a documented scikit-learn version so the `InconsistentVersionWarning` goes away for good.
2. **Bump `python-jose`** past the version CVE-2026-85394 affects, and re-pin it.
3. **Add a real dependency-vulnerability scan to CI** (`pip-audit` or `safety`, isolated to this project's own requirements files) alongside the existing `bandit` SAST job — the two catch different things.
4. **Remove the 6 `commit_msg*.txt` files** from the repo root and the empty root-level `tests/` directory (or replace it with a short README pointing at `src/tests/` and the per-MP `tests/` dirs).
5. **Fix the two CI job names** in the architecture diagram (`tls-termination-verify` and the E2E step are jobs, not separate workflow files).
6. *(Lower priority, larger effort)* Extend load testing from MP1-only to the other 4 Mega Projects.
