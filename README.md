# Home Credit RiskIQ Enterprise Suite

An end-to-end credit-risk engineering build on the [Home Credit Default
Risk](https://www.kaggle.com/competitions/home-credit-default-risk) Kaggle
dataset: real trained models, real statistical analysis, deployable scoring
services, and enterprise governance/CI — organized into **5 Mega Projects**,
each covering several of the real problems this dataset supports. (An
earlier plan included a 6th Mega Project, Behavioral Analytics — it was
dropped before any build work started, for lack of the source data/feature
columns it would have needed; see `CHANGELOG.md` [1.0.3].)

**Status**: Mega Project 1 (Underwriting & Approval Intelligence) is built,
verified, and hardened to this repo's enterprise-readiness bar. Mega
Projects 2, 3, 4, and 5 are placeholders — not yet built (see Roadmap).

## Start here

- [`mega_project_1_underwriting_approval/README.md`](mega_project_1_underwriting_approval/README.md) —
  Mega Project 1: what's built, how to run it, model cards, services, Docker.
- [`docs/suite_repository_structure.png`](docs/suite_repository_structure.png) —
  whole-suite structure: governance/CI, the shared `src/` library, Mega
  Project 1 (built) vs. the 4 placeholder Mega Projects, generated from
  [`docs/suite_repository_structure.mmd`](docs/suite_repository_structure.mmd).
- [`docs/mp1_architecture_flow.png`](docs/mp1_architecture_flow.png) —
  Mega Project 1's internal architecture flow chart (data → shared `src/`
  library → notebooks → deployable services), generated from
  [`docs/mp1_architecture_flow.mmd`](docs/mp1_architecture_flow.mmd).
- [`CHANGELOG.md`](CHANGELOG.md) — what changed in this repo, including every
  real bug found and fixed during the build.
- [`BENCHMARKS.md`](BENCHMARKS.md) — the real, measured performance numbers
  this project can honestly claim, and what is explicitly *not* benchmarked.
- [`PERFORMANCE_SETUP_README.md`](PERFORMANCE_SETUP_README.md) — the WARP
  resource-governance module.

## Mega Projects

| # | Name | Status |
|---|---|---|
| 1 | Underwriting & Approval Intelligence | **Built & hardened** — see [`mega_project_1_underwriting_approval/`](mega_project_1_underwriting_approval/) |
| 2 | Regulatory Capital | Not started — placeholder folder only |
| 3 | Risk Segmentation | Not started — placeholder folder only |
| 4 | Delinquency Prevention | Not started — placeholder folder only |
| 5 | Liquidity & Cashflow | Not started — placeholder folder only |

**Folder-naming note (resolved)**: earlier drafts of this repo had
Underwriting & Approval Intelligence checked out under
`mega_project_3_underwriting_approval/` — a leftover from before the final
1-5 Mega Project numbering was settled, while a since-dropped 6th Mega
Project (Behavioral Analytics) was still in scope. This has been corrected:
the folder is now `mega_project_1_underwriting_approval/`, matching its
actual Mega-Project-1 identity, with every service, Docker, test, and CI
path reference updated in the same change. See `CHANGELOG.md` [1.0.3] for
the full disclosure of what moved and why.

## Standing engineering principles (apply across every Mega Project)

- **Zero-fabrication**: nothing in this suite is ever run against the
  user's real data by an automated agent and reported as if verified —
  every notebook here was verified by actually executing it
  (`jupyter nbconvert --execute`) against a synthetic fixture matching the
  real Home Credit schema, confirming 0 errors, then clearing outputs
  before delivery. Running against the real, full dataset is something
  only you, in your own environment, ever does — this repo doesn't claim
  a number it hasn't itself measured.
- **WARP** (Windowed Adaptive Resource Provisioning — this suite's own
  runtime resource-governance convention): every notebook sets hard
  CPU/memory ceilings before importing any heavy library, so nothing here
  claims 100% of your machine. See `src/utils/performance_setup.py`.
- **HYPER**: shared logic (feature engineering, report building, resource
  setup, FastAPI service scaffolding) is written once in `src/` and
  imported by every notebook and service that needs it — never
  copy-pasted per problem.
- **Reproducibility**: `RANDOM_SEED = 42` everywhere randomness is
  involved.

## Repository layout

```
.
├── src/                                 # HYPER shared library (pip installable, see below)
│   ├── features/                          # feature engineering
│   ├── reporting/                          # HTML + Word + Excel report builder
│   ├── serving/                             # shared FastAPI scoring-service builder
│   └── utils/                                 # WARP performance/resource setup
├── mega_project_1_underwriting_approval/   # Mega Project 1 — built & hardened
│   ├── notebooks/                           # 01-05 problems + 06 executive rollup
│   ├── model_cards/                          # one MODEL_CARD.md per problem
│   ├── services/                              # deployable FastAPI scoring services
│   ├── docker/                                 # Dockerfile + docker-compose.yml
│   └── tests/                                   # pytest suite for the services
├── mega_project_2_regulatory_capital/      # placeholder — not yet built
├── mega_project_3_risk_segmentation/       # placeholder — not yet built
├── mega_project_4_delinquency_prevention/  # placeholder — not yet built
├── mega_project_5_liquidity_cashflow/      # placeholder — not yet built
├── data/{raw,processed}/                   # empty (.gitkeep only) — download the real dataset yourself
├── docs/                                    # architecture flow chart
└── .github/                                 # CI workflows, issue/PR templates
```

## Getting started

```bash
git clone <this repo>
cd Home_Credit_RiskIQ_Enterprise_Suite
pip install -e ".[dev,serving,explainability]"
```

Then follow [`mega_project_1_underwriting_approval/README.md`](mega_project_1_underwriting_approval/README.md)
to download the real dataset and run the notebooks.

Installing with `pip install -e .` makes the shared library importable the
same way every notebook already expects: `from features import ...`,
`from reporting.report_builder import ...`, `from utils.performance_setup
import configure_performance`, `from serving.scoring_service_common import
build_scoring_app`.

## Development

```bash
make install-dev     # editable install + dev/serving/explainability extras
make test-all         # notebook-check + pytest + lint (advisory) + bandit (blocking)
```

See the [`Makefile`](Makefile) for individual targets, and
`.github/workflows/` for exactly what CI runs on every push/PR.

## Contributing

Issue templates (bug report, feature request, model improvement) and a PR
template are in `.github/`. Please read a problem's `MODEL_CARD.md` before
proposing a model change — it documents the joblib bundle contract that the
scoring services depend on.

## License

Code is [MIT licensed](LICENSE). The Home Credit Default Risk dataset
itself is **not** redistributed in this repository — it's a Kaggle
competition dataset under Kaggle's own terms; download it directly from
Kaggle.

## Roadmap

- Build out Mega Projects 2, 3, 4, and 5 to the same standard as Mega
  Project 1 (real notebooks, hardening pass, model cards, services where
  applicable).
- Kaggle notebook/dataset packaging for Mega Project 1 (deprioritized for
  this release in favor of getting the GitHub repo and executive report
  out first).
- A repo-wide `black` reformat (currently advisory-only in CI/Makefile —
  see `CHANGELOG.md`'s "Known trade-offs").
- An actual `docker build`/`docker run` verification once Docker access is
  available (currently verified structurally only — see `BENCHMARKS.md`).
