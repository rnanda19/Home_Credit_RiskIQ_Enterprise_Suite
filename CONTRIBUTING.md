# Contributing / Development Standards

This is a solo portfolio project (not accepting external PRs at this
time), but it follows real engineering discipline so the practices
themselves are demonstrable. This document is that discipline, written
down.

## Standing rules (apply to every notebook and every module)

- **Zero-fabrication**: nothing in this suite is ever run against real
  data by an automated agent and reported as if verified. Every notebook
  here was verified by actually executing it (`jupyter nbconvert
  --execute`) against a synthetic fixture matching the real Home Credit
  schema, confirming 0 errors, then clearing outputs before delivery.
  Running against the real, full dataset is something only you, in your
  own environment, ever does — this repo doesn't claim a number it
  hasn't itself measured. Anything that can't be measured from the real
  dataset (e.g. Basel LGD / asset-correlation parameters in Mega
  Project 2) is a documented, cited assumption, never presented as
  measured.
- **One markdown intro cell + one consolidated code cell** per notebook
  (this suite's established authoring convention). Every output file is
  written to a fixed path under `decision_engine/`, overwritten in place
  (idempotent re-runs).
- **WARP** resource governance: hard CPU/memory ceilings configured
  before any heavy library import (`src/utils/performance_setup.py`), so
  a notebook never claims 100% of the host machine.
- **HYPER** shared library discipline: feature engineering, report
  building, resource setup, and FastAPI service scaffolding are written
  once in `src/` and imported by every notebook and service that needs
  them — never copy-pasted per problem.
- `RANDOM_SEED = 42` everywhere randomness is involved, for
  reproducibility.
- **No absolute/local file paths printed** in any notebook output —
  these notebooks get shared publicly.

## Code organization

- `src/` — the one shared library every Mega Project imports: `features/`
  (feature engineering, one module per Mega Project's feature set),
  `reporting/` (the HTML + Word + Excel report builder), `serving/` (the
  shared FastAPI service builders — `scoring_service_common.py` for
  trained-model services, `segment_assignment_common.py` for
  clustering-based services), and `utils/` (WARP resource governance +
  statistical checks). Nothing here is duplicated per Mega Project.
- `NN_mega_project_N_.../notebooks/` — the real, executable notebooks.
- `NN_mega_project_N_.../model_cards/` — one `MODEL_CARD.md` per problem,
  documenting the gate-by-gate verdict and (where applicable) the
  `.joblib` bundle contract a service depends on.
- `NN_mega_project_N_.../services/` — deployable FastAPI scoring/
  segment-assignment services, thin wrappers over `src/serving/`.
- `NN_mega_project_N_.../tests/` — pytest tests verifying each service's
  real output bit-identical against an independent reference computation
  (see any `tests/test_scoring_services.py` for the pattern — tests are
  skipped, not failed, when the upstream `.joblib` bundle isn't present
  locally, since that's expected until you've run the corresponding
  notebook yourself).
- `NN_mega_project_N_.../sample_reports/` — fixture-generated HTML/Word/
  Excel deliverables, clearly `SAMPLE_`-prefixed (see each folder's own
  `README.md` for the full fixture-vs-real disclosure — this suite never
  ships output derived from anyone's real data in a public repo).

## Before committing

```bash
make install-dev     # editable install + dev/serving/explainability extras
make test-all         # notebook-check + pytest (all 3 built Mega Projects) + lint (advisory) + bandit (blocking)
```

Both run in CI on every push to `main` — see `.github/workflows/ci.yml`
(notebook syntax + unit tests, matrixed across all 3 built Mega Projects)
and `code-quality.yml` (pyflakes/black advisory, bandit blocking). See
the [`Makefile`](Makefile) for individual targets.

## What NOT to do

- Don't change a notebook's actual computed output (a number, a chart, a
  model artifact) as a side effect of an infra/tooling change. If a
  change could affect output, re-run the notebook
  (`jupyter nbconvert --execute --inplace`) and re-verify end-to-end
  before committing — this repo's whole value is that every number in
  it is real, and every notebook here was executed, not simulated.
- Don't add a fabricated per-record approximation for a population-level
  analysis (e.g. RWA density, HHI concentration, Monte Carlo economic
  capital) just to give it a deployable service — several notebooks
  across this suite deliberately have no service for exactly this
  reason; see the relevant `README.md`'s services section for the
  disclosed scope boundary.
- Don't commit anything under `decision_engine/artifacts/` or
  `decision_engine/reports/` — both are gitignored everywhere in this
  repo (real trained models and real generated reports are never
  redistributed; only `sample_reports/`'s clearly `SAMPLE_`-prefixed,
  fixture-generated files are committed).
