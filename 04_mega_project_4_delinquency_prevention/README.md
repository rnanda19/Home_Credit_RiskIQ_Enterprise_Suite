# Mega Project 4 — Delinquency Prevention

**Status: not yet built.** This is a scoped placeholder reserving this
Mega Project's place in the suite (see the root README's
[Roadmap](../README.md#roadmap)). No notebooks, models, or services exist
here yet — nothing below is a claim of completed work.

## Business problem this is scoped to cover

Early-warning and delinquency-prevention analysis on the real Home Credit
dataset: identifying the leading indicators that separate an account
headed for delinquency from one that isn't, early enough for a proactive
intervention (outreach, restructuring, limit change) rather than a
downstream collections process.

## Planned approach (same standard as Mega Project 1)

- Cross-validate any new early-warning signal against Mega Project 1's
  existing PD model rather than treating it as an independent, unchecked
  claim — the same cross-validation discipline Mega Project 1's own
  notebooks 04/05 already use against its notebook 01 champion.
- Apply the same zero-fabrication, verification-protocol, and model-card
  discipline documented in
  [`01_mega_project_1_underwriting_approval/`](../01_mega_project_1_underwriting_approval/README.md).
- Ship the same dual-check pattern (structural integrity + statistical
  robustness) so any output here carries an honest, gate-based verdict
  rather than an unqualified claim.
