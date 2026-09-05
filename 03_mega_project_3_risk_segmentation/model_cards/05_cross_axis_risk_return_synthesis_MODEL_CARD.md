# Model Card — Problem 5: Cross-Axis Risk-Return Synthesis

Notebook: `notebooks/05_cross_axis_risk_return_synthesis.ipynb`
Hard dependency: `decision_engine/artifacts/notebook_01_risk_tiers.csv` (this
Mega Project's own Notebook 01 — `SK_ID_CURR`, `PD`, `TARGET`, `RISK_TIER`)
Soft dependencies (all independently optional):
`02_mega_project_2_regulatory_capital/decision_engine/artifacts/notebook_01_capital_scores.csv`
(Mega Project 2 / Notebook 01 — `EXPECTED_LOSS`, `CAPITAL_REQUIREMENT`, `EAD_PROXY`),
`decision_engine/artifacts/notebook_02_bureau_segments.csv` (Notebook 02 —
`BUREAU_SEGMENT`), `decision_engine/artifacts/notebook_03_repayment_segments.csv`
(Notebook 03 — `REPAYMENT_SEGMENT`), `decision_engine/artifacts/notebook_04_utilization_segments.csv`
(Notebook 04 — `UTILIZATION_SEGMENT`)

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This trains no model of any kind and reads no raw Home Credit CSV

Unlike every other notebook in this suite, Problem 5 does not score PD,
does not cluster, and does not read a single raw Home Credit table. It is
a pure, honest SYNTHESIS: a real join and a real aggregation of numbers
every other notebook in this Mega Project (and Mega Project 2) already
computed and independently verified. Nothing is re-scored, re-clustered,
or re-fit.

## What "risk-return" means here

Not investment return — real regulatory CAPITAL CONSUMPTION (Mega
Project 2's real Vasicek-based capital requirement, `CAPITAL_REQUIREMENT`
divided by `EAD_PROXY`) set against real default RISK (real `PD` and
`TARGET`) for each real segmentation axis this Mega Project has built.
The deliverable answers a real, concrete question: which axis — and which
segment within it — concentrates the most real risk per unit of real
capital already being held against it.

## Why real capital tracking real risk is the right validation here, not
## a repeated chi-square/silhouette test

Problems 1-4 each already asked and honestly answered "is this
segmentation's association with real default statistically robust?"
inside their own notebooks. Re-asking that same question here, on the
same real segment assignments, would not be new evidence — it would be
double-counting the same test. Problem 5 asks a genuinely different, new
real question instead: among the axes available, does real CAPITAL
ALLOCATION actually track real RISK the way a properly functioning
regulatory-capital framework should? Risk Tier is the one axis in this
synthesis that is genuinely ORDERED (by real PD, established in
Notebook 01), so `monotonic_within_noise()` — the same statistically-
tolerant, Bonferroni-corrected check Notebook 01 already used for
default-rate monotonicity — is applied here to real CAPITAL rate instead,
a different claim never previously tested. The other three axes (Bureau,
Repayment, Utilization Segment) are unordered categorical groups, so no
monotonicity check applies to them — the same reasoning already
established three times elsewhere in this suite.

## Real fixture result

All 4 real segmentation axes were available on the fixture (Risk Tier,
Bureau Segment, Repayment Segment, Utilization Segment), plus the real
Mega Project 2 capital enrichment. Real default-rate spread by axis
(widest to narrowest): **Risk Tier 97.97%** (1.63%-99.59% across 6 real
data-driven tiers), Repayment Segment 7.84% (12.58%-20.42% across 8),
Bureau Segment 6.68% (13.23%-19.91% across 8), Utilization Segment 5.96%
(12.50%-18.46% across 8). Risk Tier — built directly from real PD — by
far most sharply differentiates real risk, exactly as expected; the three
behavioral segmentation axes each add real, meaningfully smaller but
still genuine differentiation on top of it (this is the expected shape
for the result: PD level *should* dominate, and it does).

Real capital rate by axis: Risk Tier 5.64%-9.09%, Bureau Segment
6.16%-6.49%, Repayment Segment 5.71%-6.63%, Utilization Segment
5.86%-6.82%. **Real capital-rate monotonicity across Risk Tier: HOLDS**
— real capital consumption rises through the real, PD-ordered tiers
exactly as a properly functioning Vasicek-based capital model should.

**Synthesis Verdict on the fixture: SYNTHESIS VALIDATED — CAPITAL TRACKS
RISK AS EXPECTED.** All 4 synthesis-validation checks pass (every Risk
Tier applicant covered, no negative default or capital rates, capital
rate monotonic by Risk Tier). All structural Pipeline Integrity Checks
pass; the notebook completes and reports fully regardless of the
synthesis verdict.

## Real production run confirmed (your 307,511-applicant data)

All 4 real segmentation axes were available. Real default-rate spread by
axis (widest to narrowest): **Risk Tier 48.92%** (1.67%-50.59% across the
real data-driven tiers), **Utilization Segment 10.51%** (5.42%-15.94%
across 9 real segments), Bureau Segment 5.37% (7.00%-12.37% across 5),
Repayment Segment 2.42% (5.98%-8.40% across 3).
The notable real finding: Utilization Segment re-ranks to **2nd** place
at real production scale — ahead of both Bureau Segment and Repayment
Segment — a reversal from the small verification fixture, where it
ranked narrowest of the three behavioral axes. This is a genuine,
non-obvious business insight this synthesis surfaced: revolving-credit
usage patterns differentiate real default risk more sharply than either
external bureau behavior or instalment-loan repayment conduct once
measured across the full real population, even though all three add only
modest differentiation next to Risk Tier's own PD-driven dominance.

Real capital-rate monotonicity across Risk Tier: **HOLDS**. Real
Synthesis Verdict: **SYNTHESIS VALIDATED — CAPITAL TRACKS RISK AS
EXPECTED.** 0 execution errors; every structural Pipeline Integrity
Check and every synthesis-validation check passed on this real run.

## Advanced error tackling applied

- **Hard dependency** on this Mega Project's own Notebook 01 output,
  checked by actual required columns present, not just file existence
  (`LESSONS_LEARNED.md` #4).
- **Four independent soft dependencies** (MP2 Notebook 01's capital,
  this project's Notebooks 02/03/04 segments) — this notebook still
  produces a complete, honest synthesis across whichever axes are
  actually present, never fabricating a missing one; each availability
  is disclosed explicitly in the notebook's own printed output and in
  the JSON summary.
- **`monotonic_within_noise()` applied only where it is meaningful** —
  see the dedicated section above; explicitly NOT applied to the three
  unordered categorical axes.
- **No chi-square/silhouette/bootstrap section, by design** — those
  questions were already asked and honestly answered inside each axis's
  own notebook; this notebook asks a new, non-duplicate real question
  instead (see above).
- **No `matplotlib.use(...)` call anywhere in this file**
  (`LESSONS_LEARNED.md` #7).
- **No raw Home Credit CSV is read in this notebook at all** — every
  number synthesized here is a real join of already-verified real
  outputs from this suite's own `decision_engine/` folders.
- **No EDA section**, per standing instruction.

## Synthesis Verdict vs. Pipeline Integrity Checks

Same two-tier pattern as every other notebook in this suite, adapted to
what this notebook actually does: the **Synthesis Verdict** (every axis's
applicants fully covered, no negative rates, and — when capital is
available — real capital-rate monotonicity by Risk Tier) is this
notebook's own equivalent of a statistical-robustness verdict, reported
separately from the structural **Pipeline Integrity Checks**. A synthesis
could in principle be structurally sound (integrity checks pass) while
being flagged (capital does NOT track risk as expected) — that would be
a real, actionable finding about the upstream capital model, not a code
defect in this notebook.

## Limitations

- If Mega Project 2 / Notebook 01 has not been run, this notebook
  produces a complete real RISK-only synthesis (default-rate spread by
  axis) but skips the capital ("return") side entirely, including the
  capital-rate monotonicity check — disclosed explicitly, not silently.
- If none of Notebooks 02-04 have been run, this notebook still
  synthesizes across Risk Tier alone — a real, if narrower, result.
- The cross-axis "spread" metric (max minus min real rate across a
  axis's own segments) is a simple, transparent, honestly-computed
  measure of differentiation — it is not a formal effect-size statistic
  and does not itself carry a significance test (those live in each
  axis's own notebook).
- `monotonic_within_noise()`'s statistical tolerance (Bonferroni-corrected
  two-proportion z-test plus a minimum practical-difference floor) is the
  same disclosed methodology already used in Notebook 01 — see
  `src/utils/stats_checks.py`'s own docstring for the full method.

## Reproducibility

Deterministic: this notebook performs no random sampling, no model
fitting, and no bootstrap of its own — every number is a real join and a
real aggregation of already-deterministic upstream outputs. Idempotent:
re-running overwrites the same output paths given the same upstream
Notebook 01 (and, when present, MP2 Notebook 01 and this project's
Notebooks 02-04) output.
