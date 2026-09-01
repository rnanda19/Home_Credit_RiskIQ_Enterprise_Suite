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
| 4 | Delinquency Prevention | 0/6 | — | — | — | — | Scoped, not yet built |
| 5 | Liquidity & Cashflow | 0/6 | — | — | — | — | Scoped, not yet built |

Each built Mega Project's own `README.md` and `CHANGELOG.md` (in its
own folder) carry the problem-by-problem detail; this table is the
suite-wide summary.

## Hardening track — status

All 3 built Mega Projects are at full parity on:

- Real notebooks, verified end-to-end (execute → 0 errors → clear
  outputs → `nbformat` validate → Playwright network-blocked dashboard
  check → LibreOffice headless workbook recalc check).
- One `MODEL_CARD.md` per problem, documenting the gate-by-gate verdict
  and any `.joblib` bundle contract.
- Deployable FastAPI services for every problem where a per-record
  service is a meaningful thing to build (population-level analyses
  deliberately have none — see each Mega Project's own README for the
  disclosed scope boundary), with Docker Compose orchestration and a
  pytest suite verifying each service bit-identical against an
  independent reference computation.
- A complete, `SAMPLE_`-prefixed `sample_reports/` set (HTML dashboard +
  Word report + Excel workbook, every problem + the executive rollup).
- CI (`ci.yml` notebook-syntax + unit-tests, `code-quality.yml`
  pyflakes/black/bandit) running across all 3 Mega Projects.
- GitHub Pages live dashboards for all 3 Mega Projects.
- An architecture flow diagram (Mermaid + PNG) embedded directly in each
  Mega Project's own `README.md`.

## What's not yet done

- **Mega Projects 4 and 5** are scoped (see each folder's own
  placeholder `README.md`) but not yet built.
- **An actual `docker build`/`docker run`** has not been performed for
  any of the 3 built Mega Projects — verification so far is structural
  only (`docker compose config` + static `COPY`-path existence checks),
  because this build environment has no Docker daemon. See
  `BENCHMARKS.md`.
- **A repo-wide `black` reformat** is still deferred — lint is currently
  advisory (`|| true` in CI, `-black` in the Makefile), not blocking.
- **Kaggle notebook/dataset packaging** for Mega Projects 1-3 hasn't
  been done yet.
- Once all 5 Mega Projects exist, `00_executive_rollup_report/` gets a
  real, measured suite-wide rollup across all of them — currently an
  honest placeholder.

## Immediate next steps (in order)

1. Build Mega Project 4 (Delinquency Prevention) to the same standard as
   1-3: real notebooks → model cards → services/Docker/tests →
   sample_reports → CI/docs wiring.
2. Build Mega Project 5 (Liquidity & Cashflow) the same way.
3. Once both are built, produce the real suite-wide executive rollup in
   `00_executive_rollup_report/`.
4. Revisit the deferred items above (Docker build verification, `black`
   reformat, Kaggle packaging) once no new Mega Project work is
   competing for priority.
