# Changelog — Mega Project 5 (Liquidity & Cashflow)

Curated, this-Mega-Project-only view. For the full itemized history of
every change across the whole suite, see the
[root `CHANGELOG.md`](../CHANGELOG.md).

| Version | What changed |
|---|---|
| [2.1.0] | All 6 notebooks (5 problems + executive rollup) rerun end-to-end on your own real, full-scale data. Real, current result: 5/5 problems recommended for production (`rollup_verdict = "ALL AVAILABLE PROBLEMS RECOMMENDED FOR PRODUCTION"`), with Problem 5 carrying one disclosed REVIEW finding at the Severely Adverse 90-day macro stress scenario (a real business finding, not a pipeline failure). Problem 4's notebook now has real `.joblib` persistence code and a matching FastAPI service (`services/prepayment_segment_assignment_service.py`, port 8015), reusing the existing shared `segment_assignment_common.py` factory — not yet verified against a real bundle (the notebook needs one more real run). 6 new model cards, this file, and `README.md` written/updated to reflect the genuine current state. |
| [2.0.0] | Problem 1 (Portfolio Cashflow Timing & Reliability) built and verified end-to-end — the first genuinely dollar-weighted (not count-weighted) reliability view in this suite, reusing Mega Project 1's real `REPAYMENT_CAPACITY_RATIO` formula. |
| — | Problem 2 (Cash-Flow-at-Risk Rolling Forecast) built and verified — real vectorized bootstrap Monte Carlo over Problem 1's historical collection rates. |
| — | `bootstrap_cash_flow_at_risk()` extracted as a standalone, reusable HYPER function from Problem 2's own logic, so Problem 3 could reuse it directly. |
| — | Problem 3 (Retail Liquidity Coverage Proxy, Basel LCR-adapted) built and verified. |
| — | Problem 4 (Prepayment / Early-Repayment Behavior Segmentation) built and verified — real, unsupervised K-Means clustering, never trained against `TARGET`. |
| — | Problem 5 (Macro Cashflow Stress Test) built and verified — a real, deterministic Gaussian-tail macro-scenario model, reusing Mega Project 2's disclosed Z-severity convention. |
| — | Notebook 06 (Consolidated Executive Rollup, Problems 1-5) built — pure consolidation of the 5 problems' own real summaries. |

See [`README.md`](README.md) for the current problem list, and each
`model_cards/*_MODEL_CARD.md` for the real, gate-by-gate verdict of the
corresponding problem.
