# Changelog — Mega Project 4 (Delinquency Prevention)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite (including these entries in context),
see the [root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [1.9.8] | Hardening pass: 4 deployable FastAPI scoring services (Problems 1-4), hardened from day one with real `X-API-Key` auth and per-request explainability — no retrofit needed, unlike Mega Projects 1-3; Docker Compose packaging (non-root user, real health check, required `API_KEY`); a real pytest suite (bit-identical checks + 401-without-key assertions); root CI/Makefile wired up; a new architecture diagram. **Mega Project 4 built & hardened.** |
| [1.9.7] | The two shared HYPER serving-layer modules this Mega Project's services depend on (`src/serving/auth_common.py`, `src/serving/explainability_common.py`) added, as part of the suite-wide retrofit onto Mega Projects 1-3's pre-existing services. |
| [1.9.6] | Fixed a real crash found on the user's full-scale real run: Excel forbids `/` in a worksheet title, and two of this Mega Project's own problem labels contain one. New `safe_sheet_name()` in the shared `src/reporting/report_builder.py`. |
| [1.9.5] | Notebook 06 — Executive Rollup, consolidating whichever of Problems 1-5's real summaries are present. **Mega Project 4 notebooks complete, 6/6.** |
| [1.9.4] | Notebooks 04 and 05 — POS/Cash Loan Delinquency Trajectory, and Early-Warning Intervention Ranking (a real, disclosed fusion of Problems 1-4's own scores, no new training). Both built under the 2026-09-01 no-fixture policy. |
| [1.9.3] | **Policy change**: from this Mega Project's Problem 3 onward (and all later suite work), new logic is verified with small, hand-built test cases instead of a full pipeline run against a synthetic fixture. Notebook 03 — Revolving/Credit-Card Distress Early Warning — built under the new policy. |
| [1.9.2] | Fixed a real bug found on the user's real, full-scale run: `installments_payments.csv` null-payment handling. |
| [1.9.1] | Notebook 02 — Installment Payment Behavior / Missed-Payment Pattern Detection (real, unsupervised K-Means over 7 real payment-streak features). |
| [1.9.0] | **Mega Project 4 started.** Scope locked in; Notebook 01 — Early Delinquency Risk Scoring — built (4-model-screened classifier on real installment-payment behavioral features, cross-compared against Mega Project 1's champion). |

See [`README.md`](README.md) for the current problem list, architecture
diagram, and sample reports. See each `model_cards/*_MODEL_CARD.md` for
the real, gate-by-gate verdict of the corresponding problem — including
the Statistical Robustness Verdict (Problems 1, 3, 4), Clustering
Robustness Verdict (Problem 2), and Ranking Comparison (Problem 5) each
carries, versus its structural Pipeline Integrity Checks.

**A note on verification depth across this table**: Problems 1-2 (and the
services/Docker/tests added in [1.9.7]/[1.9.8]) were verified by actually
executing real code against real or synthetic inputs. Problems 3 onward
(Notebooks 03-06) were verified with hand-built test cases, a syntax/AST
check, and `nbformat.validate()` — never a full run against a fixture —
per the [1.9.3] policy change. See the root README's Standing Engineering
Principles for why, and this Mega Project's own README for the full
per-problem disclosure.
