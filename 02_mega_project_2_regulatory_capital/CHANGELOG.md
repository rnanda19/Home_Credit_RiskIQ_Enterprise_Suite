# Changelog — Mega Project 2 (Regulatory Capital & Stress Testing)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite (including these entries in context),
see the [root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [1.8.2] | This README now links its own `sample_reports/` (live dashboard, HTML, Word, Excel — every problem + rollup) and embeds the architecture diagram, instead of pointing only at the folder. |
| [1.8.1] | Root-level CI workflows, GitHub Pages, `Makefile`, and root docs updated to run this Mega Project's tests and serve its dashboards alongside Mega Project 1 and 3. |
| [1.7.0] | Hardening pass: 2 deployable FastAPI services (`capital_requirement_service.py`, `stress_testing_service.py` — Problems 2/3/5 deliberately get none, being population-level analyses), Docker packaging, a 5-test pytest suite verified bit-identical against `regulatory_capital_features.compute_capital_row()`, and the complete 18-file `sample_reports/` set. |
| [1.4.8] | Notebook 06 — Consolidated Executive Rollup. **Mega Project 2 complete, 6/6.** |
| [1.4.7] | Notebook 05 — Capital Concentration by Segment (real HHI analysis). |
| [1.4.6] | Notebook 04 — Macro Stress Testing (conditional-PD-given-Z scenarios). |
| [1.4.4] | Notebook 03 — Economic Capital & Unexpected Loss (real Monte Carlo simulation of the Vasicek model). |
| [1.4.3] | Fixed two real bugs behind an early "NOT YET STATISTICALLY ROBUST" verdict, found while investigating the user's real 307,511-applicant run of Notebook 01. |
| [1.4.2] | Notebook 02 — Basel RWA Portfolio Analytics. |
| [1.4.0] | Notebook 01 — Expected Loss & Capital Requirement Estimation. **Mega Project 2 started.** |

See [`README.md`](README.md) for the current problem list, architecture
diagram, sample reports, and the zero-fabrication disclosure on what's
real (PD, EAD) versus a documented Basel assumption (LGD, correlation) in
this Mega Project. See each `model_cards/*_MODEL_CARD.md` for the real,
gate-by-gate verdict of the corresponding problem.
