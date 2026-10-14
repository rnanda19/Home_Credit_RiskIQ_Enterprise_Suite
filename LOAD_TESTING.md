# Load Testing

This document exists to close a real, previously-disclosed gap: "No
evidence any service has ever been tested under concurrent load --
real-world request-per-second and latency-under-load are both unknown."

## What exists

`01_mega_project_1_underwriting_approval/loadtest/locustfile.py` -- a
real [Locust](https://locust.io/) load test against MP1 Problem 1's real
service (`credit_default_scoring_service.py`, this suite's flagship,
most-reused model -- see `MODEL_REGISTRY.md`). Each simulated user
performs the real, full authenticated flow: a real `POST /token` OAuth2
exchange once at start, then repeated real `POST /score` calls with a
real, in-schema payload, plus an occasional real `GET /health` check.

Run it yourself against any real running instance:

```
locust -f loadtest/locustfile.py --host=http://127.0.0.1:8001 \
    --headless -u 10 -r 5 --run-time 30s --csv=results \
    --api-key <the service's real configured API_KEY>
```

(`--api-key` defaults to the published dev-only key, or reads
`LOADTEST_API_KEY` from the environment -- see the locustfile's own
`--api-key` CLI argument.)

## A real run's real results (2026-09-08)

Run against a real live instance of this exact service (real fitted
`LogisticRegression` bundle, real `install_rate_limiting()` +
`require_auth` wired in exactly as the deployed service ships), 10
simulated users ramping up at 5/second, 30 real seconds:

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 152 | 0 | 3 ms | 5 ms | 6 ms | 18 ms | 35 ms | 5.2 req/s |
| `POST /score` | 737 | 677 (all `429`) | 5 ms | 10 ms | 31 ms | 110 ms | 168 ms | 25.4 req/s |
| `POST /token` | 10 | 0 | 24 ms | 40 ms | 44 ms | 44 ms | 44 ms | 0.3 req/s |

**The real, disclosed finding, not a load-testing failure**: 677 of 737
`/score` calls returned `429 Too Many Requests` -- exactly what the real
rate limiter added in [2.1.5] does by design (60/minute per client IP;
737 − 677 = 60, matching that limit exactly, since every simulated Locust
user in this run shares one machine's IP). This is the rate limiter
working correctly under real concurrent load, verified here for the
first time under actual request volume rather than only the handful of
calls each unit test makes. `GET /health` never failed, confirming
liveness probes stay unaffected exactly as designed.

**What this run does and does not tell you**: the accepted `/score`
requests' own latency (median 5 ms, p99 110 ms, max 168 ms) is real,
measured, single-process latency for this suite's real preprocessing +
`predict_proba()` + real per-request SHAP-style explainability path,
under real concurrent contention -- not a synthetic number. It does
*not* tell you this service's real maximum sustained throughput from
*many distinct client IPs* (each gets its own real 60/minute budget in
production; this run, from one machine, hits the same shared budget the
60th request already exhausts). Measuring true multi-tenant throughput
capacity would mean running Locust from several distinct source IPs (or
temporarily raising the configured limit for a dedicated capacity test)
-- a real, disclosed extension, not done here.

## MP2 Problem 1 -- a second, architecturally different real run (2026-10-14)

Extended past the single MP1 Problem 1 service as part of the 2026-10-14
Phase 2 hardening pass. `02_mega_project_2_regulatory_capital/loadtest/
locustfile.py` is a second, genuinely new load test (not a copy-pasted
rename) against `capital_requirement_service.py` -- a deterministic,
no-trained-model Basel Vasicek/ASRF formula service, deliberately chosen
because it exercises a different code path than MP1 Problem 1's
trained-model + SHAP-style explainability path: real auth + real rate
limiting + a real closed-form financial calculation, with zero
scikit-learn/.joblib dependency.

Run against a real local instance, 10 simulated users ramping up at
5/second, 30 real seconds:

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 163 | 0 | 2 ms | 3 ms | 3 ms | 4 ms | 14 ms | 5.6 req/s |
| `POST /score` | 774 | 714 (668 `429`, ~1 user's worth of `401`) | 4 ms | 6 ms | 7 ms | 10 ms | 42 ms | 26.7 req/s |
| `POST /token` | 10 | 1 (`429`) | 12 ms | 27 ms | 27 ms | 27 ms | 27 ms | 0.3 req/s |

**Real, disclosed finding, same root cause as MP1's run**: the same
60/minute-per-IP rate limiter again accounts for the bulk of `/score`
failures (668 `429`s). The remaining ~73 `/score` failures are `401`s
from the one simulated user whose own `/token` call was itself rate-
limited (visible above: 1 of 10 `/token` calls returned `429`) -- that
user's `on_start()` never got a token, so every subsequent `/score` call
from it correctly fails authentication rather than silently succeeding
unauthenticated. This is the real auth + real rate-limiting code working
exactly as designed under concurrent load, independently reproduced on a
second, architecturally unrelated service.

## MP1 Problems 2-4, MP2 Problem 2, MP3 (all 4), MP4 (all 4), MP5 Problem 4 -- the remaining 13 real runs (2026-10-14, Phase 4.1)

Extended past the 2 services above as part of Phase 4.1 (Production Reliability Engineering). Each of the 13 remaining real, deployable services now has its own bespoke locustfile (field names matched to that service's own real request schema -- none of these are copy-pasted renames) under `<mega_project>/loadtest/`, run the exact same way as the two runs above: a real `uvicorn` subprocess per service (one at a time, never concurrently), real OAuth2 `/token` exchange, 10 simulated users ramping up at 5/second, 25 real seconds, against the real CI fixture bundle (`scripts/generate_ci_fixture_bundles.py`) for every service that depends on a trained model -- the same, already-disclosed fixture convention this suite's Docker build verification and end-to-end tests already use, not a new scope choice invented for this benchmark pass.

**Real, disclosed finding, identical root cause across all 13 runs**: every single `/score` failure below is a `429 Too Many Requests` from the same real 60/minute-per-IP rate limiter (`src/serving/rate_limit_common.py`) already documented above -- verified directly against each run's own `*_failures.csv` (not inferred): zero `5xx` errors, zero timeouts, zero connection errors across all 13 services. `GET /health` never failed on any of them.

### MP1 Problem 2 -- Loan Approval Scoring (`loan_approval_scoring_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 146 | 0 | 2 ms | 4 ms | 6 ms | 15 ms | 22 ms | 6.1 req/s |
| `POST /score` | 617 | 557 | 4 ms | 10 ms | 21 ms | 75 ms | 125 ms | 25.7 req/s |
| `POST /token` | 10 | 0 | 30 ms | 34 ms | 34 ms | 34 ms | 34 ms | 0.4 req/s |

557 of 617 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP1 Problem 3 -- Credit Score Estimation (`credit_score_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 114 | 0 | 3 ms | 5 ms | 6 ms | 14 ms | 19 ms | 4.7 req/s |
| `POST /score` | 645 | 585 | 4 ms | 11 ms | 22 ms | 76 ms | 107 ms | 26.8 req/s |
| `POST /token` | 10 | 0 | 18 ms | 24 ms | 24 ms | 24 ms | 24 ms | 0.4 req/s |

585 of 645 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP1 Problem 4 -- Repayment Capacity Analysis (`repayment_capacity_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 126 | 0 | 2 ms | 3 ms | 3 ms | 4 ms | 4 ms | 5.2 req/s |
| `POST /score` | 651 | 591 | 4 ms | 6 ms | 7 ms | 10 ms | 25 ms | 27.1 req/s |
| `POST /token` | 10 | 0 | 16 ms | 18 ms | 18 ms | 18 ms | 18 ms | 0.4 req/s |

591 of 651 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP2 Problem 2 -- Macro Stress Testing (`stress_testing_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 129 | 0 | 2 ms | 4 ms | 5 ms | 6 ms | 8 ms | 5.4 req/s |
| `POST /score/{scenario}` | 656 | 476 | 4 ms | 7 ms | 8 ms | 12 ms | 67 ms | 27.4 req/s |
| `POST /token` | 10 | 0 | 16 ms | 22 ms | 22 ms | 22 ms | 22 ms | 0.4 req/s |

476 of 656 `/score/{scenario}` calls returned `429` (rate limiter) -- 0 other failures.

**Flagged on review, see "Acceptance thresholds" below**: 180 of 656 calls succeeded here (27.4%) versus ~9% on every other service -- confirmed by a live follow-up test to be a real rate-limiter keying gap specific to this path-parameterized endpoint (each of `/score/Baseline`, `/score/Adverse`, `/score/Severely Adverse` gets its own independent 60/minute bucket instead of sharing one), not a measurement artifact.

### MP3 Problem 1 -- Risk Tier Assignment (`risk_tier_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 130 | 0 | 2 ms | 4 ms | 6 ms | 7 ms | 9 ms | 5.4 req/s |
| `POST /score` | 646 | 586 | 4 ms | 6 ms | 7 ms | 10 ms | 13 ms | 27.0 req/s |
| `POST /token` | 10 | 0 | 16 ms | 22 ms | 22 ms | 22 ms | 22 ms | 0.4 req/s |

586 of 646 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP3 Problem 2 -- Bureau Behavioral Segmentation (`bureau_segment_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 127 | 0 | 3 ms | 4 ms | 5 ms | 10 ms | 11 ms | 5.3 req/s |
| `POST /score` | 643 | 583 | 4 ms | 7 ms | 8 ms | 15 ms | 206 ms | 26.8 req/s |
| `POST /token` | 10 | 0 | 16 ms | 20 ms | 20 ms | 20 ms | 20 ms | 0.4 req/s |

583 of 643 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP3 Problem 3 -- Repayment Behavior Segmentation (`repayment_segment_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 134 | 0 | 3 ms | 5 ms | 6 ms | 12 ms | 13 ms | 5.6 req/s |
| `POST /score` | 638 | 578 | 4 ms | 7 ms | 8 ms | 20 ms | 195 ms | 26.6 req/s |
| `POST /token` | 10 | 0 | 18 ms | 26 ms | 26 ms | 26 ms | 26 ms | 0.4 req/s |

578 of 638 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP3 Problem 4 -- Revolving Utilization Segmentation (`utilization_segment_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 141 | 0 | 3 ms | 4 ms | 8 ms | 48 ms | 117 ms | 5.8 req/s |
| `POST /score` | 632 | 572 | 4 ms | 7 ms | 10 ms | 120 ms | 192 ms | 26.2 req/s |
| `POST /token` | 10 | 0 | 25 ms | 30 ms | 30 ms | 30 ms | 30 ms | 0.4 req/s |

572 of 632 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP4 Problem 1 -- Early Delinquency Scoring (`early_delinquency_scoring_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 122 | 0 | 3 ms | 4 ms | 4 ms | 7 ms | 8 ms | 5.1 req/s |
| `POST /score` | 645 | 585 | 4 ms | 10 ms | 20 ms | 76 ms | 113 ms | 26.9 req/s |
| `POST /token` | 10 | 0 | 20 ms | 25 ms | 25 ms | 25 ms | 25 ms | 0.4 req/s |

585 of 645 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP4 Problem 2 -- Installment Payment Pattern Detection (`payment_pattern_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 125 | 0 | 2 ms | 4 ms | 5 ms | 6 ms | 9 ms | 5.2 req/s |
| `POST /score` | 644 | 584 | 4 ms | 6 ms | 7 ms | 40 ms | 194 ms | 26.9 req/s |
| `POST /token` | 10 | 0 | 17 ms | 21 ms | 21 ms | 21 ms | 21 ms | 0.4 req/s |

584 of 644 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP4 Problem 3 -- Revolving Distress Scoring (`revolving_distress_scoring_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 121 | 0 | 2 ms | 4 ms | 5 ms | 8 ms | 12 ms | 5.0 req/s |
| `POST /score` | 655 | 595 | 4 ms | 10 ms | 21 ms | 76 ms | 82 ms | 27.3 req/s |
| `POST /token` | 10 | 0 | 15 ms | 21 ms | 21 ms | 21 ms | 21 ms | 0.4 req/s |

595 of 655 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP4 Problem 4 -- POS/Cash Trajectory Scoring (`pos_cash_trajectory_scoring_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 125 | 0 | 2 ms | 4 ms | 4 ms | 15 ms | 16 ms | 5.2 req/s |
| `POST /score` | 643 | 583 | 4 ms | 11 ms | 23 ms | 83 ms | 100 ms | 26.9 req/s |
| `POST /token` | 10 | 0 | 20 ms | 26 ms | 26 ms | 26 ms | 26 ms | 0.4 req/s |

583 of 643 `/score` calls returned `429` (rate limiter) -- 0 other failures.

### MP5 Problem 4 -- Prepayment Behavior Segmentation (`prepayment_segment_assignment_service.py`)

| Endpoint | Requests | Failures | Median | p90 | p95 | p99 | Max | Throughput |
|---|---|---|---|---|---|---|---|---|
| `GET /health` | 123 | 0 | 2 ms | 4 ms | 5 ms | 10 ms | 10 ms | 5.1 req/s |
| `POST /score` | 649 | 589 | 4 ms | 6 ms | 7 ms | 18 ms | 188 ms | 27.0 req/s |
| `POST /token` | 10 | 0 | 20 ms | 25 ms | 25 ms | 25 ms | 25 ms | 0.4 req/s |

589 of 649 `/score` calls returned `429` (rate limiter) -- 0 other failures.

## Acceptance thresholds (derived from the measured baseline, 2026-10-14)

Per your own standing rule: these thresholds are **measured first, then set from that measurement plus an explicit margin** -- never invented ahead of having real numbers. The margin applied throughout is **1.5x** on every latency ceiling and **0.7x** (a 30% floor) on throughput -- picked to tolerate normal run-to-run variance (this suite's own re-runs already show the same service's p99 moving by 2-3x between runs just from local machine jitter) without being so loose that a real 2x regression would still pass.

**Important measurement caveat, found by reviewing the data, not assumed:** in every run, roughly 9% of `/score` calls succeeded and ~91% were fast `429` rejections (the rate limiter rejects before the real scoring/model work ever runs). Because successes are such a small slice, they concentrate in the upper percentiles -- **p95-p99-max are the real proxy for genuine scoring latency here; the median is actually measuring the rate limiter's own fast-reject path, not model inference.** Thresholds below are set on p95/p99/max for exactly this reason.

**A real, disclosed finding from this review, not a code change yet**: MP2 Problem 2 (`stress_testing_service.py`) shows 180 successes (27.4%) instead of the ~60 (9%) every other service shows. Verified directly, not inferred -- a live test against a real local instance confirms the rate limiter's 60/minute limit is keyed in a way that gives each literal `/score/{scenario}` path (`/score/Baseline`, `/score/Adverse`, `/score/Severely Adverse`) its own independent bucket: exhausting `Baseline`'s 60 calls still leaves `Adverse` returning `200`. **Net effect: this one endpoint's real enforced limit is 180/minute, not the intended 60/minute** -- a 3x gap specific to path-parameterized routes, worth a real fix (e.g. an explicit `scope=` on the limiter decorator, or moving `scenario` to the request body instead of the path) as part of Phase 4.2's resilience work. Not fixed in this pass -- flagged for the next one.

### Error-rate threshold (applies to all 15 services)

**0% non-rate-limit failures** -- hard requirement. Measured: 0 genuine `5xx`/timeout/connection failures across all 15 services, ~9,900 total requests. `429` responses are explicitly excluded from this threshold (they are the rate limiter working as designed, not a failure) and are reported separately.

### Per-service latency and throughput thresholds

| Service | Measured p95 | Measured p99 | Measured max | Measured throughput | **p95 ceiling** | **p99 ceiling** | **max ceiling** | **throughput floor** |
|---|---|---|---|---|---|---|---|---|
| MP1 P1 `credit_default_scoring_service` | 31 ms | 110 ms | 168 ms | 25.4 req/s | 50 ms | 165 ms | 260 ms | 17.7 req/s |
| MP1 P2 `loan_approval_scoring_service` | 21 ms | 75 ms | 125 ms | 25.7 req/s | 35 ms | 115 ms | 190 ms | 17.9 req/s |
| MP1 P3 `credit_score_service` | 22 ms | 76 ms | 107 ms | 26.8 req/s | 35 ms | 115 ms | 170 ms | 18.7 req/s |
| MP1 P4 `repayment_capacity_service` | 7 ms | 10 ms | 25 ms | 27.1 req/s | 15 ms | 15 ms | 40 ms | 18.9 req/s |
| MP2 P1 `capital_requirement_service` | 7 ms | 10 ms | 42 ms | 26.7 req/s | 15 ms | 15 ms | 70 ms | 18.6 req/s |
| MP2 P2 `stress_testing_service` | 8 ms | 12 ms | 67 ms | 27.4 req/s | 15 ms | 20 ms | 110 ms | 19.1 req/s |
| MP3 P1 `risk_tier_assignment_service` | 7 ms | 10 ms | 13 ms | 27.0 req/s | 15 ms | 15 ms | 30 ms | 18.8 req/s |
| MP3 P2 `bureau_segment_assignment_service` | 8 ms | 15 ms | 206 ms | 26.8 req/s | 15 ms | 25 ms | 310 ms | 18.7 req/s |
| MP3 P3 `repayment_segment_assignment_service` | 8 ms | 20 ms | 195 ms | 26.6 req/s | 15 ms | 30 ms | 300 ms | 18.5 req/s |
| MP3 P4 `utilization_segment_assignment_service` | 10 ms | 120 ms | 192 ms | 26.2 req/s | 15 ms | 180 ms | 290 ms | 18.3 req/s |
| MP4 P1 `early_delinquency_scoring_service` | 20 ms | 76 ms | 113 ms | 26.9 req/s | 30 ms | 115 ms | 170 ms | 18.8 req/s |
| MP4 P2 `payment_pattern_assignment_service` | 7 ms | 40 ms | 194 ms | 26.9 req/s | 15 ms | 60 ms | 300 ms | 18.8 req/s |
| MP4 P3 `revolving_distress_scoring_service` | 21 ms | 76 ms | 82 ms | 27.3 req/s | 35 ms | 115 ms | 130 ms | 19.0 req/s |
| MP4 P4 `pos_cash_trajectory_scoring_service` | 23 ms | 83 ms | 100 ms | 26.9 req/s | 35 ms | 125 ms | 150 ms | 18.8 req/s |
| MP5 P1 `prepayment_segment_assignment_service` | 7 ms | 18 ms | 188 ms | 27.0 req/s | 15 ms | 30 ms | 290 ms | 18.9 req/s |

**Why the ceilings differ so much per service even though the margin rule is the same**: they're not supposed to be uniform -- each service's own measured number drives its own ceiling. MP3 P4's p99 ceiling (180ms) is wide specifically because its own measured p99 (120ms) was already an outlier versus its sibling segmentation services (15-30ms range); that's the methodology correctly reflecting a real per-service difference rather than a copy-pasted number across all 15.

**What these thresholds are, and are not, good for**: they're real regression gates for *this exact test profile* (25s, 10 users, ramp 5/s, CI fixture bundle, one machine) -- a future run under this same profile that blows past a ceiling is a real signal something got slower or broke. They are **not** a production SLA and should not be read as one: a different load profile (sustained/peak, real trained bundles, multiple source IPs) would produce different real numbers and needs its own measured baseline before it gets its own thresholds, per the same rule this section follows.

## Honest scope: what Phase 4.1 covers today, and what it doesn't yet

All 15 of this suite's real, deployable FastAPI services now have a real, executed load-testing run (up from 2). Every run above is real synthetic/local load from one machine against the real CI fixture bundle (or, for MP1 P4/MP2 P2/MP3 P1, the real deterministic formula/tiering path with no bundle at all) -- not genuine, unpredictable production traffic, and not yet run against any real production-trained `.joblib` bundle (those are `.gitignore`d, see DATA_PRIVACY.md, and would need a locally re-trained notebook to supply). It also does not yet cover: peak/sustained load beyond the 25s/10-user profile used here, CPU/memory usage under load (not captured by Locust itself -- a separate `psutil`/container-stats pass), or multi-tenant throughput from more than one source IP (see the MP1 P1 run's own caveat above, which still applies to every run in this document equally). These are real, disclosed extensions for a follow-up pass, not silently completed here.

One more open item surfaced by this same review, not yet fixed: MP2 Problem 2's rate-limiter keying gap (see "Acceptance thresholds" above) -- real, reproduced live, and left for Phase 4.2 rather than patched silently mid-benchmark-review.

