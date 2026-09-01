# Mega Project 3 — Risk Segmentation

**Status: not yet built.** This is a scoped placeholder reserving this
Mega Project's place in the suite (see the root README's
[Roadmap](../README.md#roadmap)). No notebooks, models, or services exist
here yet — nothing below is a claim of completed work.

## Business problem this is scoped to cover

Portfolio and applicant segmentation on the real Home Credit dataset:
grouping applicants/borrowers into risk tiers that are stable and
statistically distinguishable from each other — the kind of segmentation a
collections, pricing, or portfolio-management team would use to
differentiate treatment, not a single blended risk score.

## Planned approach (same standard as Mega Project 1)

- Clustering/tiering validated the same way Mega Project 1 validates its
  risk tiers — data-driven cut points, not arbitrary thresholds, with a
  statistical significance check on whether segments are actually
  distinguishable.
- Apply the same zero-fabrication, verification-protocol, and model-card
  discipline documented in
  [`01_mega_project_1_underwriting_approval/`](../01_mega_project_1_underwriting_approval/README.md).
- Ship the same dual-check pattern (structural integrity + statistical
  robustness) so any output here carries an honest, gate-based verdict
  rather than an unqualified claim.
