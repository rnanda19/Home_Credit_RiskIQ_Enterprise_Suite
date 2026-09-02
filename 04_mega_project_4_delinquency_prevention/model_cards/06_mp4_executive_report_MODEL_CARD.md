# Model Card — Notebook 06: Consolidated Executive Rollup

Notebook: `notebooks/06_mp4_executive_report.ipynb`
Hard dependency (not owned by this notebook): whichever of Problems 1-5's
own governance summaries are present — `../decision_engine/reports/
notebook_0{1..5}_summary.json`

## Real data-quality-adjacent bug fix (2026-09-01)

On the user's real full-scale run (307,511 applicants, 5/5 real problem
summaries found), this notebook crashed while building the Excel workbook:

```
ValueError: Invalid character / found in sheet title
```

**Root cause**: this Mega Project's own real problem names for Problem 3
("Revolving/Credit-Card Distress Early Warning") and Problem 4 ("POS/Cash
Loan Delinquency Trajectory") each contain a literal real `/`, which Excel
forbids in a worksheet title. That real `/` reached `wb.create_sheet()`
unsanitized — this suite's own synthetic fixture, and every prior Mega
Project's own executive rollup, never happened to have a problem label
containing `\ / ? * [ ] :`, so this bug was latent in the shared HYPER
`report_builder.py` module and had never been triggered before.

**Fix**: added a new, HYPER `safe_sheet_name()` function to
`src/reporting/report_builder.py` that replaces the characters Excel
itself forbids in a sheet title (`\ / ? * [ ] :`) with `-`, strips a
leading/trailing apostrophe (also forbidden), and truncates to Excel's own
31-character limit — used internally by every `wb.create_sheet()` call
inside `build_excel_workbook()`, so every past and future caller (any
Mega Project's own rollup) is protected, not just this notebook. This
notebook's own two local sheet-name-construction sites (building the
per-problem data sheet, and later looking that same sheet back up by name
to embed its real chart PNG) were also updated to call the exact same
`safe_sheet_name()` function on the exact same input, so the name it
builds and the name it later looks up are always guaranteed to match. The
real, unsanitized problem label is never altered anywhere else — the
Word report, the HTML dashboard, and every chart/insight still show the
real name, e.g. "Revolving/Credit-Card Distress Early Warning" in full.

**Verification of the fix**: `safe_sheet_name()` was called directly on
all 5 of this Mega Project's real problem labels, confirming every
forbidden character is removed, the result stays within 31 characters,
and both call sites produce an identical name for the same input; a real,
direct `build_excel_workbook()` integration test was also run using the
two labels that actually crashed on the user's run ("Revolving/Credit-
Card Distress Early Warning", "POS/Cash Loan Delinquency Trajectory") —
confirmed to build a real `.xlsx` with 0 errors and the expected
sanitized sheet names (`P03 Revolving-Credit-Card`, `P04 POS-Cash Loan
Delinque`) present in the workbook.

## This is a pure rollup — no new training, no new clustering, no re-scoring

This notebook trains nothing, clusters nothing, and re-runs no fusion. It
reads each of the 5 real problem notebooks' own, already-computed
governance JSON summary and consolidates them into one executive-ready
package. A missing summary is reported and skipped, never fabricated — the
rollup is honest about partial availability if not all 5 problems have
been run. Note that every MP4 notebook writes its summary JSON to
`decision_engine/reports/`, not `decision_engine/artifacts/` (unlike Mega
Project 3) — this notebook reads from the same location every other MP4
notebook already writes to.

## The two genuinely new things this notebook adds

1. **"Real Behavioral Data Coverage"** — a fresh bar chart that
   independently re-derives each of Problems 1-4's own real scope
   population (applicants with at least one real record in that problem's
   underlying table) as a fraction of the real total applicant population,
   directly from that problem's OWN summary JSON (`n_scope` / `n_app_total`).
   This deliberately does **not** assume these fractions should be equal —
   each real behavioral table naturally covers a different real subset of
   applicants (not every applicant holds a revolving credit card or a
   POS/cash loan) — and it stands on its own even in a partial rollup that
   has not run Problem 5.
2. **Real cross-notebook consistency check** (Section 5): if Problem 5 has
   run, its own real `signals_available` record is checked here, signal by
   signal, against which of Notebooks 01-04's own summaries actually exist
   on this run — confirming no soft dependency was silently missed or
   silently faked. A separate, simpler check confirms `n_app_total` (the
   real `application_train.csv` row count) is identical across every
   available classifier/clustering notebook, since they all load the same
   real file independently.

## Three verdict-tier families, correctly labeled, never conflated

Problems 1, 3, and 4 each report a "Statistical Robustness Verdict"
(5-fold CV champion selection, real holdout ROC-AUC, bootstrap 95% CI,
decile-calibration monotonicity). Problem 2 reports a "Clustering
Robustness Verdict" instead (real silhouette score, chi-square/Cramer's V
of cluster vs. real `TARGET`) — a different validation family because it
is unsupervised. Problem 5 reports a "Ranking Comparison Verdict" instead
of either — it trains and clusters nothing; it validates a genuinely
different real question: does a real composite of Problems 1-4's signals
capture more real defaults in its top decile than the simplest possible
real comparator (current DPD). `PROBLEM_META`'s `verdict_kind` field
carries this distinction through to every output format, and a standalone
SMART insight explains it explicitly — the same disclosed pattern Mega
Project 3's own executive rollup (`06_mp3_executive_report.ipynb`) already
established for its own two-verdict-family split.

## World-class reporting package — what's actually in each format

- **Word report** (`mp4_executive_report.docx`): executive summary, up to
  7 SMART insights (one per available problem, plus 2 bonus insights
  explaining the 3 verdict-tier families and how real behavioral-data
  coverage varies by product line), one section per problem with that
  problem's own already-verified real chart PNG embedded (never redrawn),
  and a dedicated "Real Behavioral Data Coverage" section with this
  notebook's one new synthesis chart.
- **Excel workbook** (`mp4_executive_report.xlsx`): a big-letters
  "Executive Rollup" front sheet (inserted first) with headline real KPIs
  and a native, editable openpyxl `BarChart` of real behavioral-data
  coverage built from real cell data on that same sheet; one sheet per
  problem, each with that problem's own real chart PNG embedded via
  `openpyxl.drawing.image`; a Problem Rollup sheet; a Behavioral Coverage
  sheet; an Assumptions sheet with real, formula-driven figures
  (blue-font/yellow-fill convention); a Financial Impact sheet whose
  values are real Excel formulas referencing the Assumptions sheet (not
  precomputed numbers); and a SMART Insights sheet.
- **HTML dashboard** (`mp4_executive_dashboard.html`): real KPI cards, up
  to 5 charts (Real Behavioral Data Coverage; a real holdout-ROC-AUC
  comparison across Problems 1/3/4's classifiers; a real default-rate-by-
  payment-pattern chart for Problem 2; a real composite-vs-naive
  top-decile chart for Problem 5; and a verdict-distribution doughnut), a
  Key Insights & SMART Recommendations grid, and a searchable/filterable
  per-problem rollup table.

## Advanced error tackling applied

- Missing upstream summaries reported and skipped, never fabricated
  (`LESSONS_LEARNED.md` — same posture as Mega Projects 1, 2, and 3's own
  executive rollups).
- Real cross-checks, not asserted (`LESSONS_LEARNED.md` #6): both checks
  in Section 5 compare real records computed by independent notebooks —
  never a hard-coded "should be true" assertion.
- Each problem's own already-verified real chart PNG is reused directly in
  both the Word report and the Excel workbook rather than redrawn —
  nothing in this notebook can silently drift from what that problem's own
  verification pass already confirmed correct.
- "Real Behavioral Data Coverage" is deliberately built from Problems
  1-4's OWN summaries, not from Problem 5's derived output — so a partial
  rollup (Problem 5 not yet run) still produces a complete, honest
  coverage comparison.
- The Notebook 05 signal-availability cross-check is skipped (not marked a
  failure) when Notebook 05 itself has not been run — a real, disclosed
  distinction between "not yet checkable" and "checked and failed."

## Verification status (2026-09-01 policy change)

Per explicit instruction, this notebook was **not** executed against any
synthetic fixture before delivery. It trains, clusters, and fits nothing
new — it only reads, joins, and re-presents real JSON already produced by
Notebooks 01-05. Its two genuinely new pieces of derived logic — the real
coverage-ratio computation (Section 4) and the real cross-notebook
signal-availability consistency check (Section 5) — were verified with 3
small, hand-built mock-summary test cases: full availability (all 5
present, all consistent), partial availability with a deliberate signal
mismatch (Notebook 05 claims a signal is available that has no matching
notebook summary present), and a deliberate `n_app_total` mismatch across
notebooks. In every case, the coverage fractions, sort order, and exactly
which consistency check(s) failed were checked by hand against the input
and confirmed exact — including that the deliberate mismatches were
correctly caught and correctly named, and that the non-mismatch cases were
correctly confirmed. This file's syntax was checked (`py_compile`/
`ast.parse`, 0 errors) and this notebook passes `nbformat.validate()`.
**No rollup number, no coverage figure, no consistency result has been
computed by us for this notebook.** Those are determined only by running
this notebook after whichever of Notebooks 01-05 you have run against your
real, downloaded Home Credit dataset.

## Limitations

- This notebook cannot recover a problem's real figures if that problem's
  own summary JSON is missing or stale — it always reflects whatever each
  of Notebooks 01-05 was MOST RECENTLY run against, and says so explicitly
  in every output format.
- The Notebook 05 signal-availability cross-check assumes Notebook 05 was
  run against the same underlying real data as Notebooks 01-04 — if you
  ran Notebook 05 before re-running an upstream notebook after a data or
  code change, this check compares a stale record, not a contradiction in
  the current code.
- No fairness/bias audit performed in this pass, consistent with every
  other MP4 notebook.
- No production scoring service for this notebook — it is a reporting
  rollup, not a per-record scoring endpoint.

## How to reproduce

1. Download the real Home Credit Default Risk dataset from Kaggle.
2. Set up `project_config.json` per the notebook's own first markdown cell.
3. Run as many of Notebooks 01-05 as you have available first (soft
   dependencies — this notebook runs with as few as 1 of the 5 present,
   and raises a clear error if 0 are present rather than fabricating a
   rollup).
4. Run `notebooks/06_mp4_executive_report.ipynb` end-to-end.
5. The real rollup package is written to `decision_engine/reports/`:
   `mp4_executive_report.docx`, `mp4_executive_report.xlsx`,
   `mp4_executive_dashboard.html`, plus supporting CSVs and
   `mp4_executive_summary.json`.
