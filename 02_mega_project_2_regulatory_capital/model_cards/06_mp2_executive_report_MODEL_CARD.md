# Model Card — Notebook 06: Consolidated Executive Rollup

Notebook: `notebooks/06_mp2_executive_report.ipynb`
Hard dependency (not owned by this notebook): all 5 problem notebooks' governance
summaries — `../decision_engine/artifacts/notebook_0{1..5}_summary.json`

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This is a pure rollup — no new PD/LGD/EAD/correlation value, no re-simulation

This notebook trains nothing, scores nothing, and re-runs no simulation. It
reads each of the 5 real problem notebooks' own, already-computed governance
JSON summary and consolidates them into one executive-ready package. A
missing summary is reported and skipped, never fabricated — the rollup is
honest about partial availability if not all 5 problems have been run.

## The two genuinely new things this notebook adds

1. **The "Three Real Lenses on Capital" comparison.** The same real
   portfolio's capital number appears three different ways across this Mega
   Project: (1) Pillar-1 Baseline (Notebook 01 — the Basel closed-form
   regulatory minimum under normal conditions), (2) 99.9% Economic Capital
   via Monte Carlo (Notebook 03 — an independent numerical cross-check on
   (1), at the SAME 99.9th-percentile severity Basel's own formula is
   calibrated to), and (3) Stressed Capital under Adverse / Severely
   Adverse macro scenarios (Notebook 04 — a "what if" re-evaluation of (1)
   at a documented adverse severity). These three real numbers are placed
   side by side here explicitly to be **compared, never summed** — summing
   them would double- or triple-count the same portfolio's capital under
   mutually exclusive conditions. This is disclosed in the module
   docstring, the Word report's dedicated section, the HTML dashboard's
   chart story, and a standalone SMART insight — four independent places,
   deliberately, because this is the single most likely misreading of this
   Mega Project's output.
2. **Three real cross-notebook consistency checks** (Section 5): (a)
   Notebook 01's baseline capital is checked against Notebook 04's own
   independently-reported baseline capital and Notebook 03's closed-form
   reference number — both should trace to the identical real computation;
   (b) stressed capital is checked to increase strictly with scenario
   severity (Baseline < Adverse < Severely Adverse — a real mathematical
   guarantee of the single-factor model); (c) every real HHI value across
   every dimension is checked to fall within its valid [0, 10,000] point
   range. None of these are asserted — all three are computed and printed.

## World-class reporting package — what's actually in each format

- **Word report** (`mp2_executive_report.docx`): executive summary, 7 SMART
  insights (one per available problem, plus 2 bonus insights explaining the
  3 verdict-tier families and the Three-Lenses non-additivity), one section
  per problem with that problem's own already-verified real chart PNG
  embedded (never redrawn), and a dedicated "Three Real Lenses" section
  with this notebook's one new synthesis chart.
- **Excel workbook** (`mp2_executive_report.xlsx`), 10 sheets: a big-letters
  "Executive Rollup" front sheet (inserted first) with headline real KPIs
  and a native, editable openpyxl `BarChart` of the Three Real Lenses built
  from real cell data on that same sheet; one sheet per problem, each with
  that problem's own real chart PNG embedded via `openpyxl.drawing.image`
  PLUS a second native Excel `BarChart` built from that problem's own real
  per-category numbers (segment capital, RWA density by band, VaR/ES/EC by
  confidence level, capital by scenario, or HHI by dimension); a Problem
  Rollup sheet; an Assumptions sheet with real, formula-driven figures
  (blue-font/yellow-fill convention); a Financial Impact sheet whose values
  are real Excel formulas referencing the Assumptions sheet (not
  precomputed numbers — confirmed to recalculate correctly under LibreOffice
  headless, see Verification below); and a SMART Insights sheet.
- **HTML dashboard** (`mp2_executive_dashboard.html`): 8 real KPI cards, 7
  charts, a Key Insights & SMART Recommendations grid, and a
  searchable/filterable per-problem rollup table. **2 of the 7 charts carry
  a real, tested dropdown slicer** — "RWA Density by Segment" switches
  across all 4 real dimensions Notebook 02 examined, and "Capital Share by
  Segment" switches across all 5 real dimensions Notebook 05 examined —
  each rebuilding the chart from a different real precomputed view, never
  inventing data client-side. This was verified with an actual browser
  interaction test (see Verification below), not just visual inspection.

## Advanced error tackling applied

- Missing upstream summaries reported and skipped, never fabricated
  (`LESSONS_LEARNED.md` — same posture as Mega Project 1's own executive
  rollup).
- Real cross-checks, not asserted (`LESSONS_LEARNED.md` #6): all 3 checks
  in Section 5 compare real numbers computed by 2 different notebooks, or
  compare a real number against its own mathematical bound — never a
  hard-coded "should be true" assertion.
- Each problem's own already-verified real chart PNG is reused directly in
  both the Word report and the Excel workbook rather than redrawn — nothing
  in this notebook can silently drift from what that problem's own
  verification pass already confirmed correct.

## Verification

Verified end-to-end on the user's own real, full-scale 307,511-applicant
rerun (2026-09-02): 0 execution errors, all 6 rollup integrity checks pass
(including all 3 cross-notebook consistency checks), `nbformat.validate()`
clean before and after clearing outputs. HTML dashboard confirmed under a
network-blocked Playwright check (0 external network requests attempted, 0
page/console errors, all 7 canvases rendered) — **and the 2 dropdown
slicers were driven programmatically in that same check and confirmed to
actually change the rendered chart's labels**, not just visually inspected.
Excel workbook confirmed via LibreOffice headless recalculation — every
Financial Impact sheet formula recalculated to the exact same values
already printed by the notebook's own real run (Pillar-1 baseline
$9,756,908,313; 99.9% EC (MC) $9,915,102,034; 1.62% relative difference;
Severely Adverse $20,536,046,971; +110.5% vs. baseline — all on the user's
own real, full-scale 2026-09-02 rerun).

## Limitations

- This notebook cannot recover a problem's real figures if that problem's
  own summary JSON is missing or stale — it always reflects whatever each
  of Notebooks 01-05 was MOST RECENTLY run against, fixture or real, and
  says so explicitly in every output format.
- The Three Lenses comparison assumes Notebooks 01, 03, and 04 were all run
  against the SAME underlying data (same fixture, or same real run) — the
  cross-notebook consistency checks in Section 5 exist specifically to
  catch the case where they were not (e.g., Notebook 04 re-run on a newer
  Notebook 01 output than Notebook 03 was cross-checked against).
- No new financial ROI/benefit timeline is computed here (unlike Mega
  Project 1's executive rollup) — Mega Project 2's outputs are regulatory
  capital figures, not illustrative cost-savings figures, so a "benefit
  run-rate" framing would not honestly describe what these 5 problems
  measure.

## Reproducibility

Deterministic — no random sampling in this notebook itself (it only reads
already-computed JSON). Idempotent: re-running overwrites the same output
paths given the same 5 upstream summary files.
