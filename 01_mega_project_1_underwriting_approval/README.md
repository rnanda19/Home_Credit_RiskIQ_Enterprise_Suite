# Mega Project 1 — Underwriting & Approval Intelligence

Part of the **Home Credit RiskIQ Enterprise Suite**. See the [root
README](../README.md) for the full 5-Mega-Project roadmap and how this
folder fits in.

> **Folder name note (resolved in [1.0.3])**: this folder was previously
> checked out as `mega_project_3_underwriting_approval/` — a leftover from
> before the suite's final 1-5 Mega Project numbering was settled. It has
> since been renamed to `01_mega_project_1_underwriting_approval/`, matching
> its actual identity as the first Mega Project to reach enterprise-grade
> status, with every service, Docker, test, and CI path reference updated
> in the same change and all 6 notebooks re-verified end-to-end after the
> rename. See the root `CHANGELOG.md` [1.0.3] entry for the full disclosure.

## Problems in this Mega Project

| # | Problem | Notebook | Model card | Service |
|---|---|---|---|---|
| 1 | Credit Default Prediction | `notebooks/01_credit_default_prediction.ipynb` | [model card](model_cards/01_credit_default_prediction_MODEL_CARD.md) | `credit_default_scoring_service.py` :8001 |
| 3 | Loan Application Approval | `notebooks/02_loan_application_approval.ipynb` | [model card](model_cards/02_loan_application_approval_MODEL_CARD.md) | `loan_approval_scoring_service.py` :8002 |
| 4 | Credit Score Estimation (PDO scorecard) | `notebooks/03_credit_score_estimation.ipynb` | [model card](model_cards/03_credit_score_estimation_MODEL_CARD.md) | `credit_score_service.py` :8003 |
| 11 | Repayment Capacity Analysis | `notebooks/04_repayment_capacity_analysis.ipynb` | [model card](model_cards/04_repayment_capacity_analysis_MODEL_CARD.md) | `repayment_capacity_service.py` :8004 (ratios only — see model card) |
| 12 | Previous Application Outcomes | `notebooks/05_previous_application_outcomes.ipynb` | [model card](model_cards/05_previous_application_outcomes_MODEL_CARD.md) | none — portfolio-level analysis, see model card |
| — | Executive Rollup (all 5 above) | `notebooks/06_mp1_executive_report.ipynb` | n/a — not a model | none |

All 5 problem notebooks are independently runnable; several also
cross-validate against Notebook 01's real champion model when its bundle
is present (see each model card's "Relationship to..." / "Cross-validated
against..." section). Notebook 06 must be run **last** — it consolidates
the real illustrative dollar-impact figures already written to each
notebook's own JSON artifact, and produces nothing new of its own.

## Standing rules (apply to every notebook here)

- **Zero-fabrication**: notebooks only ever run against real data you
  provide (the Kaggle dataset) or, for this repo's own verification, a
  synthetic fixture matching the real schema — never against a description
  of what the real output "should" look like.
- **WARP** resource governance: CPU/memory ceilings are configured before
  any heavy library import (`src/utils/performance_setup.py`), so a
  notebook never claims 100% of the host machine.
- **HYPER** shared library: feature engineering, reporting, and serving
  code live once in `src/` and are imported by every notebook/service here
  — not copy-pasted per problem.
- `RANDOM_SEED = 42` everywhere randomness is involved, for reproducibility.
- One markdown cell + one consolidated code cell per notebook (this suite's
  established notebook-authoring convention).
- No absolute local file paths are ever printed in notebook output.
- Every notebook was executed for real (`jupyter nbconvert --execute`)
  against a synthetic fixture during this build's verification, confirmed
  0 errors, then had its outputs cleared before delivery — see the root
  README's verification-protocol section for the full checklist this
  repo's contents were held to.

## Running the notebooks

1. Download the real **Home Credit Default Risk** dataset from Kaggle (not
   redistributed in this repo — see `data/raw/.gitkeep` at the suite root
   and the note in `LICENSE`).
2. Create `project_config.json` at the suite root — see any notebook's
   first markdown cell for the exact expected format/paths.
3. `pip install -e ".[dev,serving,explainability]"` from the suite root (or
   just `pip install -r requirements.txt` if you don't need the optional
   groups).
4. Run notebooks 01 → 02 → 03 → 04 → 05 → 06, in that order, so each
   notebook's optional cross-validation against upstream artifacts has
   something real to check against. (01, 02, 04, and 05 will each still
   run standalone if you skip ahead — only their optional cross-checks are
   affected.)
5. Outputs land in `decision_engine/artifacts/` (trained model bundles,
   `.png` charts) and `decision_engine/reports/` (per-notebook JSON/HTML/
   Word/Excel reports plus Notebook 06's consolidated executive report),
   overwritten in place on every run.

## Running the scoring services

```bash
# from the suite root, after running notebooks 01/02 so their .joblib bundles exist
pip install -r 01_mega_project_1_underwriting_approval/services/requirements-services.txt
export PYTHONPATH="$PWD/src:$PWD/01_mega_project_1_underwriting_approval/services"
uvicorn credit_default_scoring_service:app --port 8001   # Problem 1
uvicorn loan_approval_scoring_service:app --port 8002    # Problem 3
uvicorn credit_score_service:app --port 8003             # Problem 4
uvicorn repayment_capacity_service:app --port 8004        # Problem 11
```

Or via Docker Compose (build context is the **suite root**, not this
folder — see the comment at the top of `docker/docker-compose.yml`):

```bash
# from the suite root
docker compose -f 01_mega_project_1_underwriting_approval/docker/docker-compose.yml up --build
```

**Honesty note**: the Docker files were verified structurally in this
build's environment (`docker compose config`, plus a static COPY-path
resolution check) — there is no Docker daemon or registry access in the
build sandbox, so an actual `docker build`/`docker run` has **not** been
performed by this project. Treat it as untested until you build it
yourself; see `BENCHMARKS.md` at the suite root.

## Tests

```bash
cd 01_mega_project_1_underwriting_approval && python -m pytest tests/ -v
```

5 tests in `tests/test_scoring_services.py` check each service's output
against an independent reference computation. Tests for a given service
are skipped (not failed) when that service's upstream `.joblib` bundle
isn't present locally — this is expected until you've run the
corresponding notebook.

## Folder structure

```
01_mega_project_1_underwriting_approval/
├── notebooks/         # 01-05 problem notebooks + 06 executive rollup
├── model_cards/        # one MODEL_CARD.md per problem
├── services/           # FastAPI scoring services (thin wrappers over src/serving/)
├── docker/              # Dockerfile + docker-compose.yml (suite-root build context)
├── tests/                # pytest suite for the services
└── decision_engine/
    ├── artifacts/        # trained model bundles (.joblib) + chart .png files (gitignored)
    └── reports/           # per-notebook JSON/HTML/Word/Excel reports (gitignored)
```
