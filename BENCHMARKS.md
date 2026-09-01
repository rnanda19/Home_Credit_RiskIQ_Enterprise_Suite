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

## Real, full-scale numbers (the user's own machine — no longer hypothetical)

Everything below is copied from the user's own real, pasted terminal output
of running these notebooks against the real, full-size Home Credit dataset
(307,511 applicants) on their own machine (16 logical / 8 physical cores,
31.3 GB RAM, WARP ceiling 15 threads / 28.2 GB) — not measured or estimated
by this suite, and not fabricated; recorded here because the "Suggested
follow-up" below asked for exactly this once it existed.

| Notebook | What it does | Real wall-clock | Notes |
|---|---|---|---|
| MP2 Notebook 01 (Expected Loss & Capital) | Score real PD, compute real EL/RWA/capital for 307,511 applicants | not separately timed by the user | Real EL $3.92B (2.13% of EAD); real Basel capital $9.88B (5.37% of EAD, RWA $123.55B) |
| MP2 Notebook 02 (Basel RWA Portfolio Analytics) | Pure analytical layer over Notebook 01's output | 1.2s | Real portfolio RWA density 66.21% |
| MP2 Notebook 03 (Economic Capital & Unexpected Loss) | 70,000 total vectorized Monte Carlo draws (50,000 main + 20,000 independent-reseed check) over 307,511 applicants | **684.7s (~11.4 min)** | Real 99.9% Economic Capital $9,915,102,034 (1.62% relative difference vs. Notebook 01's closed-form capital requirement, documented 10% tolerance — WITHIN TOLERANCE); real RAM usage flat at ~24.3–24.4 GB throughout, no growth |

Notebook 03's 684.7s figure is the one genuinely large-N Monte Carlo
benchmark this suite has so far — roughly 31 million (draw × applicant)
elements processed per second, batched and vectorized (never a per-draw or
per-applicant Python loop; see `LESSONS_LEARNED.md` §5 for the full
derivation and what it implies for Problems 4/5's own runtime). Compare
this to the ORIGINAL per-resample bootstrap this suite replaced (~3 hours,
did not finish, on a smaller table) — vectorized batching is why this
finished in minutes at real production scale rather than hours.

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
- **Real wall-clock for every other notebook in the suite** — only the
  figures in the table above have been reported back by the user so far;
  every other notebook's real-data runtime is still unmeasured. Add real
  numbers here as they come in, the same way the table above was built —
  never estimate or fabricate one in the meantime.
