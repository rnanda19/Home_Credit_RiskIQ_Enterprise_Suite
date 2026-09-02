# Changelog — Mega Project 1 (Underwriting & Approval Intelligence)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite (including these entries in context),
see the [root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [1.8.3] | Added the missing 6th model card (`model_cards/06_mp1_executive_report_MODEL_CARD.md`), built from the real `mp1_executive_summary.json` — this Mega Project now has all 6 model cards, matching Mega Projects 2-5. |
| [1.8.2] | This README now links its own `sample_reports/` (live dashboard, HTML, Word, Excel — every problem + rollup) and embeds the architecture diagram, instead of pointing only at the folder. |
| [1.8.1] | Fixed a real stale-path bug in `docker/Dockerfile` and `docker-compose.yml`, left over from the `[1.1.0]` restructure and never caught until the Mega Project 2/3 hardening pass found it. GitHub Pages, both CI workflows, and root docs updated to include Mega Projects 2 and 3 alongside this one. |
| [1.6.2] | Problem numbering fixed to match Mega Project 2 / Mega Project 3's convention (this suite's original global 1/3/4/11/12 numbering renumbered to local 1-5 + 6 for the rollup). |
| [1.4.1] | Notebook 01 retrained on all 7 real Home Credit data tables (was 2) — a real scope expansion; every downstream notebook re-verified against the new champion bundle. |
| [1.3.0] | GitHub Pages live dashboard hosting added; corrected README claims about how GitHub actually renders linked `.html`/`.docx`/`.xlsx` files when clicked. |
| [1.2.1] | Full sample reports added — real HTML/Word/Excel deliverables for all 5 problems + the executive rollup, clearly `SAMPLE_`-prefixed. |
| [1.2.0] | README and documentation rewritten for a hiring-manager/recruiter audience — no code or notebook content changed. |
| [1.1.0] | Repository restructured to a flat, numbered, self-contained project layout — this folder's current identity. |
| [1.0.3] | Corrected the Mega Project numbering to its final 5-project scope; completed this folder's rename from a leftover mismatched name. |
| [1.0.2] | Statistically-principled monotonicity-check methodology revision, fully disclosed. |
| [1.0.1] | Fixed misleading (not incorrect) executive-report verdict text. |
| [1.0.0] | Original hardening pass — 4 deployable FastAPI scoring services, Docker packaging, pytest suite, CI (`ci.yml` + `code-quality.yml`), and governance files (LICENSE, issue/PR templates), bringing this Mega Project to the same enterprise-readiness bar established on this account's AMEX Credit Risk Platform (Phase 2 hardening). |

See [`README.md`](README.md) for the current problem list, architecture
diagram, and sample reports, and each `model_cards/*_MODEL_CARD.md` for
the real, gate-by-gate verdict of the corresponding problem.
