# Changelog — Mega Project 3 (Risk Segmentation)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite (including these entries in context),
see the [root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [1.9.10] | Completed the real-data correction pass: README.md's Problems 1, 2, and 4 sections now carry their own real, confirmed 307,511-applicant verdicts (all three STATISTICALLY ROBUST — RECOMMENDED FOR PRODUCTION, alongside Problem 3's already-corrected real NOT YET STATISTICALLY ROBUST finding) instead of stopping at the fixture-only result. Fixed a real transcription error in the Problem 5 real-data paragraph (Bureau Segment default-rate spread was mis-stated as 2.98%; the real value from notebook_05_summary.json is 5.37%; Repayment Segment corrected from 2.44% to the exact 2.42%). Removed the now-deleted `sample_reports/` fixture-demo links from the README's Sample Reports table and folder-structure diagram (those files were removed from the repo since real per-notebook reports now exist). All 6 `model_cards/*.md` files corrected the same way — Model Cards 01, 02, and 04 gained a real "Real production run confirmed" section; Model Card 03's two remaining stale fixture-only sentences were corrected to reference the real, already-confirmed NOT YET STATISTICALLY ROBUST verdict; Model Card 06 gained a real executive-rollup confirmation ($52,803,356.03 real total annual financial-impact benefit, all 5 problem summaries found, all cross-notebook consistency checks at 0.00 max absolute difference). |
| [1.9.9] | Rerun end-to-end on your own real, full-scale data (307,511 real applicants). Genuine current result: 4/5 problems recommended for production — Problem 3 (Repayment Behavior Segmentation) is real and confirmed **NOT YET STATISTICALLY ROBUST** (fails `cramers_v_ci_excludes_zero`), consistent with its own model card. `README.md`'s Notebook 06 section corrected — it previously described a small 4,000-row fixture run and incorrectly said "Not yet run against your real data," though this real run already existed. |
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
