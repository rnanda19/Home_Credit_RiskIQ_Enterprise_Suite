# Changelog — Mega Project 3 (Risk Segmentation)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite (including these entries in context),
see the [root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [1.8.2] | This README now links its own `sample_reports/` (live dashboard, HTML, Word, Excel — every problem + rollup) and embeds the architecture diagram, instead of listing none at all. |
| [1.8.1] | Root-level CI workflows, GitHub Pages, `Makefile`, and root docs updated to run this Mega Project's tests and serve its dashboards alongside Mega Project 1 and 2. |
| [1.8.0] | Hardening pass: Notebooks 02/03/04 now persist their real, chosen K-Means model + fitted `StandardScaler` (+ winsorize bounds) to a new `.joblib` bundle; `src/serving/segment_assignment_common.py` (new shared builder); 4 deployable FastAPI segment-assignment services; Docker packaging; a 4-test pytest suite verified against real applicants already present in each notebook's own output; the complete 18-file `sample_reports/` set. |
| [1.6.10] | Notebook 06 — Consolidated Executive Rollup. **Mega Project 3 complete, 6/6.** |
| [1.6.9] | Notebook 05 — Cross-Axis Risk-Return Synthesis. |
| [1.6.8] | Notebook 04 — Revolving Credit Utilization Segmentation. |
| [1.6.7] | Notebook 03 verified end-to-end on real 307,511-applicant data. |
| [1.6.6] | Notebook 03: stability floor lowered from 3% to 1%, empirically grounded. |
| [1.6.5] | Notebook 03: K candidate range widened to include k=2. |
| [1.6.4] | Notebook 03: fixed a real-data K-Means outlier-domination bug. |
| [1.6.3] | Notebook 03 — Repayment Behavior Segmentation. |
| [1.6.1] | Notebook 02 — Credit Bureau Behavioral Segmentation. |
| [1.6.0] | Notebook 01 — Data-Driven Risk Tier Construction. **Mega Project 3 started, 1/6.** |

See [`README.md`](README.md) for the current problem list, architecture
diagram, and sample reports. See each `model_cards/*_MODEL_CARD.md` for
the real, gate-by-gate verdict of the corresponding problem — including
each clustering notebook's Statistical Robustness Verdict versus its
structural Pipeline Integrity Checks.
