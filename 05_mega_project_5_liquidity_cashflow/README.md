# Mega Project 5 — Liquidity & Cashflow

**Status: not yet built.** This is a scoped placeholder reserving this
Mega Project's place in the suite (see the root README's
[Roadmap](../README.md#roadmap)). No notebooks, models, or services exist
here yet — nothing below is a claim of completed work.

## Business problem this is scoped to cover

Liquidity and cashflow-pattern analysis on the real Home Credit dataset:
reading repayment-capacity and cashflow-timing signals (building on Mega
Project 1's repayment-capacity work) at a portfolio level — the kind of
view a treasury or ALM (asset-liability management) function would use to
understand incoming-cashflow reliability, not a claim of an
institution-wide liquidity model.

## Planned approach (same standard as Mega Project 1)

- Build on Mega Project 1's repayment-capacity ratios (notebook 04) rather
  than recompute them independently, consistent with this suite's HYPER
  (shared-logic) principle.
- Apply the same zero-fabrication, verification-protocol, and model-card
  discipline documented in
  [`01_mega_project_1_underwriting_approval/`](../01_mega_project_1_underwriting_approval/README.md).
- Ship the same dual-check pattern (structural integrity + statistical
  robustness) so any output here carries an honest, gate-based verdict
  rather than an unqualified claim.
