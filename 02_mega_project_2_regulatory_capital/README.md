# Mega Project 2 — Regulatory Capital

**Status: not yet built (in this repo).** This is a scoped placeholder
reserving this Mega Project's place in the suite (see the root README's
[Roadmap](../README.md#roadmap)). No notebooks, models, or services are
checked into this repository for this problem yet — nothing below is a
claim of completed work.

## Business problem this is scoped to cover

Regulatory-capital and risk-weighted-asset (RWA) style analysis on the real
Home Credit dataset: translating a portfolio's estimated probability of
default (PD) and exposure characteristics into the kind of capital-adequacy
view a risk or finance function needs — the analytical layer underneath a
Basel-style capital calculation, not a claim of producing an actual
regulatory RWA figure.

## Planned approach (same standard as Mega Project 1)

- Reuse Mega Project 1's champion PD model rather than retrain from
  scratch, consistent with this suite's HYPER (shared-logic) principle.
- Apply the same zero-fabrication, verification-protocol, and model-card
  discipline documented in
  [`01_mega_project_1_underwriting_approval/`](../01_mega_project_1_underwriting_approval/README.md).
- Ship the same dual-check pattern (structural integrity + statistical
  robustness) so any output here carries an honest, gate-based verdict
  rather than an unqualified claim.
