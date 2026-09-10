import nbformat as nbf

nb = nbf.v4.new_notebook()

markdown_cell = nbf.v4.new_markdown_cell(source="""# Mega Project 4 — Delinquency Prevention
## Problem 6: Executive Rollup
## Consolidating Problems 1-5's Own Real Results — No New Model, No New Clustering, No New Scoring

**Home Credit Default Risk — 5 Mega Projects Enterprise Suite**

### Business context
A portfolio-risk stakeholder does not want five separate notebooks — they
want one real answer to "what did Mega Project 4 find, and can I trust it."
This notebook consolidates Problems 1-5's own real, already-computed
results into a single executive report, with nothing recomputed, retrained,
re-clustered, or invented along the way.

### This notebook trains, clusters, and fits nothing new
It is a real, disclosed **rollup** of whichever of Problems 1-5's own
already-computed real governance summaries (`decision_engine/reports/
notebook_0N_summary.json`) are present on disk — each is a SOFT dependency,
loaded only if that notebook has already been run, never fabricated for a
missing one. Every chart embedded for a given problem is that problem's own
already-generated real PNG, reused directly, not redrawn — so nothing here
can silently drift from what that notebook's own verification pass already
confirmed.

### Two things this notebook genuinely adds
1. **Real Behavioral Data Coverage** — Problems 1-4 each score a different
   real subset of the applicant base (only applicants with at least one
   real record in that problem's underlying table). This notebook
   independently re-derives each problem's real coverage fraction — scope
   population divided by the real total applicant population — straight
   from that problem's own summary, and charts them side by side. This
   works even if Problem 5 has not been run.
2. **Real cross-notebook consistency check** — if Problem 5 has run, its
   own real record of which of Problems 1-4's signals it found available is
   checked here, signal by signal, against which of those notebooks'
   summaries actually exist on this run — confirming no soft dependency was
   silently missed or silently faked.

### Why THREE different verdict-tier names appear in this rollup
Problems 1, 3, and 4 each report a "Statistical Robustness Verdict" (5-fold
CV champion, real holdout ROC-AUC, bootstrap 95% CI, decile-calibration
monotonicity). Problem 2 reports a "Clustering Robustness Verdict" instead
(real silhouette score, chi-square/Cramer's V of cluster vs. real TARGET) —
a different validation family because it is unsupervised. Problem 5 reports
a "Ranking Comparison Verdict" instead of either — it trains and clusters
nothing; it validates a different real question: does a real composite of
Problems 1-4's signals out-rank the simplest possible real comparator
(current DPD). This rollup surfaces all three side by side, correctly
labeled, never conflated — the same disclosed pattern Mega Project 3's own
executive rollup (`06_mp3_executive_report.ipynb`) already established for
its own two-verdict-family split.

### Real bug fix (2026-09-01)
On your real full-scale run, this notebook crashed while building the
Excel workbook: `ValueError: Invalid character / found in sheet title`.
Root cause: two of this Mega Project's own real problem names —
"Revolving/Credit-Card Distress Early Warning" (Problem 3) and "POS/Cash
Loan Delinquency Trajectory" (Problem 4) — contain a literal real `/`,
which Excel forbids in a worksheet title, and which reached
`wb.create_sheet()` unsanitized. Fixed with a new, HYPER
`safe_sheet_name()` helper added to `src/reporting/report_builder.py`
(replaces the forbidden characters `\ / ? * [ ] :` with `-`, never alters
the real label anywhere else — reports, charts, and insights all keep the
real, unsanitized name) and used everywhere this notebook builds or looks
up an Excel sheet name, so the name it creates and the name it later
looks up (to embed a chart) always match. This also protects every other
Mega Project's own executive rollup against the same class of bug, should
a future problem name ever contain one of these characters.

### HYPER reuse
`src/reporting/report_builder.py` (including the new `safe_sheet_name()`
fix above) — reused for all 3 output formats (Word, Excel, HTML). No
feature-engineering module is used by this notebook; it reads only JSON
and CSV each prior notebook already wrote.

### Running this notebook
Run as many of Notebooks 01-05 as you have first — this notebook rolls up
whichever of their real outputs it finds (1 of 5 is enough to run, though
the rollup is naturally more complete with more). If zero are present, this
notebook raises a clear error rather than fabricating a rollup.

### Verification status (2026-09-01 policy)
Per explicit instruction, this notebook was **not** executed against any
synthetic fixture before delivery. It trains, clusters, and fits nothing
new — it only reads, joins, and re-presents real JSON already produced by
Notebooks 01-05. Its two genuinely new pieces of logic (the real
coverage-ratio computation and the real cross-notebook signal-availability
consistency check) were verified with 3 small, hand-built mock-summary test
cases — full availability, partial availability with a deliberate signal
mismatch, and a deliberate `n_app_total` mismatch — every derived value
(coverage fractions, sort order, consistency flags, and exactly which
check(s) fail) checked by hand against the input and confirmed exact.

The 2026-09-01 sheet-naming bug fix above was verified by calling
`safe_sheet_name()` directly on all 5 of this Mega Project's real problem
labels (confirming every forbidden character is removed and both call
sites produce an identical name) and by a real, direct
`build_excel_workbook()` integration test using the two labels that
actually crashed on your run — confirmed to build a real `.xlsx` with 0
errors and the expected sanitized sheet names present. This
file's syntax was checked (`py_compile`/`ast.parse`, 0 errors) and this
notebook passes `nbformat.validate()`. **No rollup number, no coverage
figure, no consistency result has been computed by us for this notebook.**
Those are determined only by running this notebook after whichever of
Notebooks 01-05 you have run against your real, downloaded Home Credit
dataset.
""")

with open("pipeline_mp4_nb06.py") as f:
    code_source = f.read()

code_cell = nbf.v4.new_code_cell(source=code_source)

nb["cells"] = [markdown_cell, code_cell]
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}

with open("06_mp4_executive_report.ipynb", "w") as f:
    nbf.write(nb, f)

print("ipynb written")
