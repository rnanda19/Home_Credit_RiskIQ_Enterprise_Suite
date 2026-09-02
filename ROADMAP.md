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
| 5 | Liquidity & Cashflow | 6/6 | 5/5 | 0 verified (Problem 4 code exists, not yet run against a real bundle) | — | partial | — | **Built & verified**, hardening in progress |

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

Mega Projects 1-4 are at full parity on:

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
  independent reference computation. 14 services total across Mega
  Projects 1-4.
- CI (`ci.yml` notebook-syntax + unit-tests, `code-quality.yml`
  pyflakes/black/bandit) running across Mega Projects 1-4.
- GitHub Pages live dashboards for all 3 of Mega Projects 1-3's problems,
  plus Mega Project 4's Problems 1-2 (the only ones with a fixture-
  generated dashboard to publish).
- An architecture flow diagram (Mermaid + PNG) embedded directly in each
  Mega Project's own `README.md`.
- **Real `X-API-Key` authentication on every `/schema` and `/score`
  endpoint of all 14 deployable services** (`/health` stays open, for
  liveness probes), plus real per-request explainability
  (`"top_reasons"` on every classifier-backed service,
  `"distance_to_each_segment"` on every clustering-backed one). Retrofit
  onto the 10 pre-existing Mega Project 1-3 services in [1.9.7]; built in
  from day one for Mega Project 4's 4 new services in [1.9.8] — closing
  this suite's own version of the exact gap the AMEX RiskIQ Enterprise
  Credit Risk Platform's own hardening history documents having found and
  fixed in itself. See `CHANGELOG.md` [1.9.7]/[1.9.8] for the full detail.

Mega Project 5 is built (6/6 notebooks) and verified end-to-end, with all
5 problems recommended for production — but its own hardening pass
(documentation parity, Problem 4's deployable service, CI/Makefile
wiring) is still in progress; see its own `README.md`/`CHANGELOG.md` for
current status.

## What's not yet done

- **Mega Project 5's Problem 4 service** has real persistence code and a
  real FastAPI service written, but no `.joblib` bundle has been produced
  by a real run yet — the service is not yet verified against real data.
  Re-run Notebook 04 to produce the bundle, then the service can be
  verified for real.
- **Mega Project 5's documentation hardening** (model cards, CHANGELOG,
  CI/Makefile wiring for its services/tests, architecture diagram) is in
  progress.
- **An actual `docker build`/`docker run`** has not been performed for
  any of the hardened Mega Projects — verification so far is structural
  only (`docker compose config` + static `COPY`-path existence checks),
  because this build environment has no Docker daemon. See
  `BENCHMARKS.md`.
- **A repo-wide `black` reformat** is still deferred — lint is currently
  advisory (`|| true` in CI, `-black` in the Makefile), not blocking.
- **Kaggle notebook/dataset packaging** hasn't been done yet.
- **Mega Project 1's own executive-rollup model card**
  (`06_..._MODEL_CARD.md`) is not yet written — Mega Projects 2-4 each
  have one, Mega Project 1 currently only has the 5 problem-level cards.

## Immediate next steps (in order)

1. Re-run Mega Project 5 Notebook 4 to produce the real `.joblib` bundle,
   then verify its deployable service against that real bundle.
2. Complete Mega Project 5's documentation hardening (model cards,
   CHANGELOG, CI/Makefile wiring, architecture diagram) to bring it to
   parity with Mega Projects 1-4.
3. Write Mega Project 1's missing executive-rollup model card.
4. Revisit the deferred items above (Docker build verification, `black`
   reformat, Kaggle packaging) once the above is complete.
