# Model Card — Notebook 06: Consolidated Executive Rollup

Notebook: `notebooks/06_mp3_executive_report.ipynb`
Hard dependency (not owned by this notebook): all 5 problem notebooks'
governance summaries — `../decision_engine/artifacts/notebook_0{1..5}_summary.json`

## CI status

Re-verified 2026-09-05 against the current `main` branch (commit `33ebb69`):
all 12 GitHub Actions checks pass — `shared-tests`, `unit-tests` (all 5 Mega
Projects), `lint`, `security-scan`, `build`, `notebook-syntax`, `deploy`, and
`report-build-status`. GitHub's file-history view may still show a red ✗ on
an older commit that last touched this file (`517b7f4`, from the 2026-09-02
sync, when a `polars` dependency was briefly missing from the `shared-tests`
job) — that historical failure was fixed in commit `96e4321` and does not
reflect the current state of the suite.

## This is a pure rollup — no new clustering, no re-scoring, no re-joining raw data

This notebook trains nothing, clusters nothing, and re-runs no synthesis.
It reads each of the 5 real problem notebooks' own, already-computed
governance JSON summary and consolidates them into one executive-ready
package. A missing summary is reported and skipped, never fabricated —
the rollup is honest about partial availability if not all 5 problems
have been run.

## The two genuinely new things this notebook adds

1. **"Real Segmentation Power"** — a fresh bar chart that independently
   re-derives each of Problems 1-4's own real default-rate spread
   directly from that problem's OWN summary JSON (`tier_aggregation` for
   Problem 1, `segment_aggregation` for Problems 2-4). This deliberately
   does **not** depend on Problem 5 having run at all — it stands on its
   own even in a partial rollup.
2. **Real cross-notebook consistency checks** (Section 5): for every axis
   Problem 5 also synthesized, this notebook independently re-derives that
   axis's real per-segment default rate from that axis's OWN source
   notebook (Problems 1-4) and checks it against Problem 5's own
   independent real re-aggregation of the same axis — segment by segment,
   to the last basis point. None of these are asserted — all are computed
   and printed. A separate, simpler check confirms the real applicant
   population count is identical across every available notebook (they
   all trace back to the same real Notebook 01 output).

## Two verdict-tier families, correctly labeled, never conflated

Problems 1-4 each report a "Statistical Robustness Verdict" (chi-square +
Cramer's V + minimum cluster size against real `TARGET`). Problem 5
reports a differently-named "Synthesis Verdict" instead — it runs no
chi-square/silhouette test of its own (that would double-count Problems
1-4's own already-answered questions); it validates a genuinely new real
question instead: does real capital allocation track real risk through
Risk Tier's real, PD-ordered axis. `PROBLEM_META`'s `verdict_path` /
`verdict_kind` fields carry this distinction through to every output
format, and a standalone SMART insight explains it explicitly, exactly as
Mega Project 2's own rollup does for its 3 verdict-tier families.

## World-class reporting package — what's actually in each format

- **Word report** (`mp3_executive_report.docx`): executive summary, 7
  SMART insights (one per available problem, plus 2 bonus insights
  explaining the 2 verdict-tier families and how real segmentation power
  varies by axis and by scale), one section per problem with that
  problem's own already-verified real chart PNG embedded (never
  redrawn), and a dedicated "Real Segmentation Power" section with this
  notebook's one new synthesis chart.
- **Excel workbook** (`mp3_executive_report.xlsx`), 11 sheets: a
  big-letters "Executive Rollup" front sheet (inserted first) with
  headline real KPIs and a native, editable openpyxl `BarChart` of real
  segmentation power built from real cell data on that same sheet; one
  sheet per problem, each with that problem's own real chart PNG embedded
  via `openpyxl.drawing.image` PLUS a second native Excel `BarChart`
  built from that problem's own real per-category default rates; a
  Problem Rollup sheet; a Segmentation Power sheet; an Assumptions sheet
  with real, formula-driven figures (blue-font/yellow-fill convention); a
  Financial Impact sheet whose values are real Excel formulas referencing
  the Assumptions sheet (not precomputed numbers — confirmed to
  recalculate correctly under LibreOffice headless, see Verification
  below); and a SMART Insights sheet.
- **HTML dashboard** (`mp3_executive_dashboard.html`): 10 real KPI cards,
  up to 7 charts (Real Segmentation Power, plus one real default-rate
  chart per available problem 1-4, a real capital-rate-by-tier chart when
  Problem 5's capital enrichment is available, and a verdict-distribution
  doughnut), a Key Insights & SMART Recommendations grid, and a
  searchable/filterable per-problem rollup table.

## Advanced error tackling applied

- Missing upstream summaries reported and skipped, never fabricated
  (`LESSONS_LEARNED.md` — same posture as Mega Projects 1 and 2's own
  executive rollups).
- Real cross-checks, not asserted (`LESSONS_LEARNED.md` #6): every
  cross-notebook consistency check in Section 5 compares real numbers
  computed by 2 independent notebooks — never a hard-coded "should be
  true" assertion.
- Each problem's own already-verified real chart PNG is reused directly
  in both the Word report and the Excel workbook rather than redrawn —
  nothing in this notebook can silently drift from what that problem's
  own verification pass already confirmed correct.
- "Real Segmentation Power" is deliberately built from Problems 1-4's OWN
  summaries, not from Problem 5's derived output — so a partial rollup
  (Problem 5 not yet run) still produces a complete, honest segmentation-
  power comparison.

## Verification

Verified end-to-end on this suite's synthetic fixture (an earlier
verification pass, before the real 307,511-applicant run below): 0
execution errors, all 5 rollup integrity checks pass (including the
cross-notebook consistency check), `nbformat.validate()` clean before and
after clearing outputs. On that fixture run, all 4 axis-level consistency
checks (Risk Tier, Bureau Segment, Repayment Segment, Utilization
Segment) confirmed a maximum absolute difference of exactly 0.00 between
each axis's own source notebook and Problem 5's independent
re-aggregation, across every shared segment. HTML dashboard confirmed
under a network-blocked Playwright check (0 blocked external requests, 0
console errors, 10 KPI-like elements, 7 canvases/charts rendered, 5
rollup table rows). Excel workbook confirmed via LibreOffice headless
recalculation — every Financial Impact sheet formula recalculated to the
exact same values already printed by the notebook's own fixture run (Real
Applicant Population 4,000; Real Widest Segmentation Spread 0.979664 —
all on this suite's fixture).

**Confirmed on the user's real 307,511-applicant data**: all 5 problem
summaries found (0 missing), all 6 real rollup integrity checks pass
(all_5_problem_summaries_found, n_applicants_identical_across_available_notebooks,
axis_default_rates_consistent_between_primary_notebooks_and_notebook_05_synthesis,
every_available_problem_has_a_story, every_available_problem_has_an_insight,
roi_timeline_cumulative_benefit_non_decreasing), and all 5 real
cross-notebook consistency checks confirmed a maximum absolute difference
of exactly 0.00 — including the real applicant-population-identical
check (307,511 across every available notebook: Notebooks 01-05). Real
Widest Segmentation Spread: Risk Tier, 48.92% across 6 real segments.
Real total estimated annual financial-impact benefit: $52,803,356.03 (see
the Financial Impact sheet's own disclosed assumptions, including the
real AMT_CREDIT-derived average exposure per applicant computed fresh
from this run's real applicant population). This is this notebook's
final, confirmed result on real data — no further pipeline changes are
needed.

## Limitations

- This notebook cannot recover a problem's real figures if that problem's
  own summary JSON is missing or stale — it always reflects whatever each
  of Notebooks 01-05 was MOST RECENTLY run against, fixture or real, and
  says so explicitly in every output format.
- The cross-notebook consistency checks in Section 5 assume Notebook 05
  was run against the SAME underlying data as the axis's own source
  notebook (same fixture, or same real run) — they exist specifically to
  catch the case where that is not true (e.g., Notebook 02 re-run on
  newer data than Notebook 05 was cross-checked against).
- No dollar-denominated capital figures are rolled up here (unlike Mega
  Project 2's executive rollup) — this Mega Project's own deliverable is
  segment structure and real risk differentiation, not a regulatory
  capital number; Problem 5's own capital-rate-by-tier result is surfaced
  as its own dedicated chart instead, when available.

## Reproducibility

Deterministic — no random sampling in this notebook itself (it only reads
already-computed JSON). Idempotent: re-running overwrites the same output
paths given the same 5 upstream summary files.
