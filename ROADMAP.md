# Roadmap

Forward-looking status and next steps for the suite. For the full,
itemized, version-by-version history of every real fix, rename, and
scope change already made, see [`CHANGELOG.md`](CHANGELOG.md) — this
file is the summary and what's-next view; `CHANGELOG.md` is the
detailed record.

## Mega Project status

| # | Mega Project | Notebooks | Services | Docker | Tests | Sample reports | Status |
|---|---|---|---|---|---|---|---|
| 1 | Underwriting & Approval Intelligence | 6/6 | 4 | ✅ | ✅ | 18 files | **Built & hardened** |
| 2 | Regulatory Capital & Stress Testing | 6/6 | 2 | ✅ | ✅ | 18 files | **Built & hardened** |
| 3 | Risk Segmentation | 6/6 | 4 | ✅ | ✅ | 18 files | **Built & hardened** |
| 4 | Delinquency Prevention | 6/6 | 4 | ✅ | ✅ | 6 files (Problems 1-2 only — see below) | **Built & hardened** |
| 5 | Liquidity & Cashflow | 0/6 | — | — | — | — | Scoped, not yet built |

Each built Mega Project's own `README.md` and `CHANGELOG.md` (in its
own folder) carry the problem-by-problem detail; this table is the
suite-wide summary.

## Hardening track — status

All 4 built Mega Projects are at full parity on:

- Real notebooks, verified end-to-end (execute → 0 errors → clear
  outputs → `nbformat` validate → Playwright network-blocked dashboard
  check → LibreOffice headless workbook recalc check) — **except Mega
  Project 4's Problems 3-6**, which per an explicit 2026-09-01 policy
  change were instead verified with small, hand-built test cases plus a
  syntax/AST check and `nbformat.validate()`, with no fixture execution;
  see that Mega Project's own README for the full disclosure. This is
  also why Mega Project 4's `sample_reports/` has only 6 files (Problems
  1-2) rather than the 18 each of Mega Projects 1-3 has.
- One `MODEL_CARD.md` per problem, documenting the gate-by-gate verdict
  and any `.joblib` bundle contract.
- Deployable FastAPI services for every problem where a per-record
  service is a meaningful thing to build (population-level analyses
  deliberately have none — see each Mega Project's own README for the
  disclosed scope boundary), with Docker Compose orchestration and a
  pytest suite verifying each service bit-identical against an
  independent reference computation.
- CI (`ci.yml` notebook-syntax + unit-tests, `code-quality.yml`
  pyflakes/black/bandit) running across all 4 Mega Projects.
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

## What's not yet done

- **Mega Project 5** is still scoped only (see its folder's own
  placeholder `README.md`) and not yet built.
- **An actual `docker build`/`docker run`** has not been performed for
  any of the 4 hardened Mega Projects — verification so far is structural
  only (`docker compose config` + static `COPY`-path existence checks),
  because this build environment has no Docker daemon. See
  `BENCHMARKS.md`.
- **A repo-wide `black` reformat** is still deferred — lint is currently
  advisory (`|| true` in CI, `-black` in the Makefile), not blocking.
- **Kaggle notebook/dataset packaging** for Mega Projects 1-4 hasn't
  been done yet.
- Once all 5 Mega Projects exist, `00_executive_rollup_report/` gets a
  real, measured suite-wide rollup across all of them — currently an
  honest placeholder.

## Immediate next steps (in order)

1. Build Mega Project 5 (Liquidity & Cashflow) the same way Mega Projects
   1-4 were each built, then hardened as a whole once its notebooks are
   complete (services, Docker, pytest, CI, architecture diagram).
2. Once it's built, produce the real suite-wide executive rollup in
   `00_executive_rollup_report/`.
3. Revisit the deferred items above (Docker build verification, `black`
   reformat, Kaggle packaging) once no new Mega Project work is
   competing for priority.
