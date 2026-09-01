# Home Credit RiskIQ Enterprise Suite

![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Code Quality](https://img.shields.io/badge/code%20quality-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Methodology](https://img.shields.io/badge/methodology-CRISP--DM-informational)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

An end-to-end credit-risk engineering build on the [Home Credit Default
Risk](https://www.kaggle.com/competitions/home-credit-default-risk) Kaggle
dataset: real trained models, real statistical analysis, deployable scoring
services, and enterprise governance/CI — organized into **5 Mega Projects**,
each covering several of the real problems this dataset supports.

## Status — 1 of 5 Mega Projects built

**Mega Project 1 (Underwriting & Approval Intelligence) is built, verified,
and hardened.** Mega Projects 2–5 are placeholder folders only — not yet
built. This README states that plainly rather than implying a fuller build:
every claim below about "what's real" applies to Mega Project 1 alone. See
[`00_executive_rollup_report/README.md`](00_executive_rollup_report/README.md)
for why this repo doesn't (yet) show a suite-wide number.

(An earlier plan included a 6th Mega Project, Behavioral Analytics — it was
dropped before any build work started, for lack of the source data/feature
columns it would have needed; see `CHANGELOG.md` [1.0.3].)

## Table of Contents

- [Platform at a Glance](#platform-at-a-glance)
- [Repository Structure](#repository-structure)
- [How to Run](#how-to-run)
- [Standing Engineering Principles](#standing-engineering-principles-apply-across-every-mega-project)
- [Technologies Used](#technologies-used)
- [Roadmap](#roadmap)
- [Repository Hardening](#repository-hardening)
- [Contributing](#contributing)
- [License](#license)

## Platform at a Glance

These are structural, build-verification facts about this repository —
**not** a dollar-impact claim. This project never runs against your real
data itself and never reports a number it hasn't measured; the illustrative
$ figures a notebook run produces on your own machine are yours to read in
your own `decision_engine/reports/`, not restated here as a suite-wide
figure (see [Status](#status--1-of-5-mega-projects-built) above).

| Metric | Value |
|---|---|
| Mega Projects built / planned | 1 / 5 |
| Real problems covered (Mega Project 1) | 5 (Problems 1, 3, 4, 11, 12) |
| Notebooks (Mega Project 1) | 6 — 5 problem notebooks + 1 executive rollup |
| Deployable scoring services (Mega Project 1) | 4 (FastAPI, Docker Compose) |
| Verification protocol per notebook | execute end-to-end (0 errors) → clear outputs → `nbformat` validate → LibreOffice headless recalc on every generated workbook → Playwright network-blocked check on every dashboard |
| Model cards | 1 per problem, documenting the joblib bundle contract each service depends on |
| Reproducibility | `RANDOM_SEED = 42` everywhere randomness is involved |

## Repository Structure

```
.
├── 00_executive_rollup_report/             # suite-wide rollup — honest placeholder until MP2-5 exist
├── src/                                     # HYPER shared library (pip installable, see below)
│   ├── features/                              # feature engineering
│   ├── reporting/                              # HTML + Word + Excel report builder
│   ├── serving/                                 # shared FastAPI scoring-service builder
│   └── utils/                                     # WARP performance/resource setup
├── 01_mega_project_1_underwriting_approval/  # Mega Project 1 — built & hardened
│   ├── README.md
│   ├── notebooks/                              # 01-05 problems + 06 executive rollup
│   ├── model_cards/                             # one MODEL_CARD.md per problem
│   ├── services/                                 # deployable FastAPI scoring services
│   ├── docker/                                     # Dockerfile + docker-compose.yml
│   └── tests/                                       # pytest suite for the services
├── 02_mega_project_2_regulatory_capital/     # placeholder — not yet built
├── 03_mega_project_3_risk_segmentation/      # placeholder — not yet built
├── 04_mega_project_4_delinquency_prevention/ # placeholder — not yet built
├── 05_mega_project_5_liquidity_cashflow/     # placeholder — not yet built
├── data/{raw,processed}/                     # empty (.gitkeep only) — download the real dataset yourself
├── docs/                                      # architecture flow charts
└── .github/                                   # CI workflows, issue/PR templates
```

**The leading `NN_` on each Mega Project folder is a cosmetic
display-ordering prefix only** — it makes GitHub's default alphabetical
file listing render in the same 1-5 order as the table above. It is not
part of any Mega Project's identity: code, notebooks, and reports inside
each folder still refer to "Mega Project 1," "Mega Project 2," etc.,
unprefixed.

## How to Run

```bash
git clone https://github.com/rnanda19/Home_Credit_RiskIQ_Enterprise_Suite.git
cd Home_Credit_RiskIQ_Enterprise_Suite
pip install -e ".[dev,serving,explainability]"
```

Then follow
[`01_mega_project_1_underwriting_approval/README.md`](01_mega_project_1_underwriting_approval/README.md)
to download the real dataset and run notebooks **01 → 02 → 03 → 04 → 05 →
06**, in that order — 03, 04, and 05 load the champion model bundle that 01
and 02 produce, and 06 (the executive rollup) consolidates all five
notebooks' reports, so it must run last.

Installing with `pip install -e .` makes the shared library importable the
same way every notebook already expects: `from features import ...`,
`from reporting.report_builder import ...`, `from utils.performance_setup
import configure_performance`, `from serving.scoring_service_common import
build_scoring_app`.

```bash
make install-dev     # editable install + dev/serving/explainability extras
make test-all         # notebook-check + pytest + lint (advisory) + bandit (blocking)
```

See the [`Makefile`](Makefile) for individual targets, and
`.github/workflows/` for exactly what CI runs on every push/PR (`ci.yml` —
notebook syntax + unit tests; `code-quality.yml` — pyflakes/black advisory,
bandit blocking).

## Standing Engineering Principles (apply across every Mega Project)

- **Zero-fabrication**: nothing in this suite is ever run against real data
  by an automated agent and reported as if verified — every notebook here
  was verified by actually executing it (`jupyter nbconvert --execute`)
  against a synthetic fixture matching the real Home Credit schema,
  confirming 0 errors, then clearing outputs before delivery. Running
  against the real, full dataset is something only you, in your own
  environment, ever does — this repo doesn't claim a number it hasn't
  itself measured.
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

## Technologies Used

Python 3.10+ · pandas/NumPy · scikit-learn, XGBoost, CatBoost, LightGBM ·
SHAP + LIME (explainability) · FastAPI (scoring services) · Docker /
Docker Compose · pytest · pyflakes + black (advisory lint) · bandit
(blocking security scan) · Jupyter/`nbconvert` (execution + validation) ·
LibreOffice headless (workbook recalculation check) · Playwright
(dashboard network-isolation check) · GitHub Actions (CI).

## Roadmap

- Build out Mega Projects 2, 3, 4, and 5 to the same standard as Mega
  Project 1 (real notebooks, hardening pass, model cards, services where
  applicable) — once at least one more is built,
  `00_executive_rollup_report/` gets a real, measured suite-wide rollup.
- Kaggle notebook/dataset packaging for Mega Project 1 (deprioritized for
  this release in favor of getting the GitHub repo and executive report
  out first).
- A repo-wide `black` reformat (currently advisory-only in CI/Makefile —
  see `CHANGELOG.md`'s "Known trade-offs").
- An actual `docker build`/`docker run` verification once Docker access is
  available (currently verified structurally only — see `BENCHMARKS.md`).

## Repository Hardening

This repo has been through several disclosed hardening passes — every real
bug found and fixed, every folder-naming correction, and every scope
change is written up in [`CHANGELOG.md`](CHANGELOG.md), most recently:

- **[1.1.0]** — repository restructured to this account's flat, numbered
  portfolio-repo convention (this change).
- **[1.0.3]** — corrected the Mega Project numbering to its final 5-project
  scope and moved Mega Project 1 out of a leftover mismatched folder name.
- **[1.0.2]** — a real monotonicity-methodology fix.
- **[1.0.1]** — a real verdict-text fix.
- **[1.0.0]** — the original hardening pass (see `BENCHMARKS.md` for the
  real performance fix found and measured during it: a ~3,000x reduction
  in Notebook 05's bootstrap validation step).

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
