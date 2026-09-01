# Benchmarks

Honesty note first: every number on this page was either (a) measured during
this build's own verification runs, on synthetic fixture data matching the
real Home Credit schema (never on the user's real dataset — see the
zero-fabrication note in the root README), or (b) a controlled, isolated
timing comparison run before a fix was applied to the real notebook code.
Nothing here is a production-scale claim about your actual ~307K/1.67M-row
tables — those will differ by hardware, data skew, and how much of the real
data is actually loaded. Treat these as directional evidence the fixes work,
not as SLAs.

## Notebook 05 — bootstrap validation performance fix

**Problem**: `05_previous_application_outcomes.ipynb`'s chi-square bootstrap
significance test resampled category pairs with replacement and rebuilt a
`pandas.crosstab` on every iteration, over a ~1.67M-row table. Cost scaled
with row count, ran single-threaded, and got zero benefit from the suite's
configured CPU ceiling (WARP) since the bottleneck was per-call Python/pandas
overhead, not compute parallelism.

**Fix**: the per-resample crosstab rebuild is mathematically identical to
drawing directly from `Multinomial(n, p)`, where `p` is the real empirical
joint-cell-proportion distribution already computed once for the actual
(non-bootstrap) chi-square statistic. Replaced the resample loop with one
`numpy.random.Generator.multinomial(n, p)` draw per iteration — cost is now
independent of row count.

**Measured** (controlled timing benchmark, isolated cell, before applying to
the real notebook):

| | Per-iteration cost | Iterations | Estimated total |
|---|---|---|---|
| Before (crosstab rebuild) | ~1,137 ms | 1,000 | ~19 minutes |
| After (multinomial draw) | ~0.36 ms | 1,000 | ~0.36 seconds |

**~3,000x** reduction in this section, verified by re-running the real
notebook end-to-end against the synthetic fixture afterward (0 errors) and
confirmed the resulting p-value/statistic is the same real quantity, not an
approximation.

## Verification-run execution (synthetic fixtures)

Every notebook in this project is executed for real via
`jupyter nbconvert --execute` against a synthetic fixture (same schema/dtypes
as the real Kaggle tables, small row counts) as part of the delivery
protocol for this suite — this is a correctness check (0 errors, then
outputs are cleared before delivery), not a performance benchmark, and
fixture row counts are intentionally far smaller than the real dataset, so
no wall-clock number from those runs is reported here as representative of
real-data runtime.

## What is *not* benchmarked here

- **Docker image build/run time and container resource usage** — not
  measured, because no Docker daemon or registry is available in the build
  sandbox. The `Dockerfile`/`docker-compose.yml` were verified structurally
  (via `docker compose config` and a static COPY-path resolution check)
  but never actually built or run. Treat this as untested until you build
  it yourself.
- **FastAPI service latency/throughput** under load — the 5 pytest tests in
  `test_scoring_services.py` verify correctness (service output matches an
  independent reference computation), not latency or concurrency behavior.
- **Any runtime figure against the real, full-size Home Credit dataset** —
  by design, this project never runs against the user's real data (see the
  zero-fabrication policy in the root README); only the user's own
  environment can produce that number.

## Suggested follow-up (not done in this pass)

If real-scale benchmark numbers are wanted, the honest way to get them is:
run `jupyter nbconvert --execute` on each notebook against the real,
downloaded Kaggle dataset in your own environment, and record the wall-clock
time and peak memory (`utils.performance_setup` already exposes a resource-
ceiling / logging hook for this — see `PERFORMANCE_SETUP_README.md`). That
real number belongs in this file once you have it; this project will not
fabricate one in the meantime.
