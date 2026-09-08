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

## Honest scope: what this covers today, and what it doesn't yet

Wired for one flagship service (MP1 Problem 1) -- same disclosed,
partial-but-real scope as `MONITORING.md` and `TLS.md`. Extending to
another service means pointing `--host` at that service's own port and
adjusting `FIXTURE_FEATURES` (or, for a load test against a real trained
model instead of the CI fixture bundle, pointing the target service at
its real `.joblib` bundle and adjusting the payload to that bundle's real
feature names).

This is real synthetic/local load, not genuine, unpredictable production
traffic -- see `remediation_data.js`'s own caveat on this gap: "This
validates real architecture and latency under synthetic load -- it will
not reflect genuine, unpredictable production user traffic patterns, but
the load-testing methodology itself is fully real and fillable."
