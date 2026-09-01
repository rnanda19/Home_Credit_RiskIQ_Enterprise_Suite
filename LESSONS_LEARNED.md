# Lessons Learned — Pre-Flight Checklist for Every New Notebook

This file exists so Mega Project 3 onward — and every notebook after it —
do **not** re-discover, one real bug at a time, issues this suite has
already paid for once. Read this before writing a new notebook's first
line of code, and again before calling it done. Every item below is a
real, disclosed incident from this suite's own build/verification history
(cross-referenced to `CHANGELOG.md`), not a hypothetical. Mega Project 2
(all 6 notebooks) is the source of every lesson below and is now complete
and confirmed working on real data — this file carries forward everything
it cost to learn that.

## 1. Editing a `pipeline_*.py` source file does NOT change the `.ipynb`

**What happened**: Problem 1's directionality bug ([1.4.3]) was fixed in
`pipeline_mp2_nb01.py`, the notebook was re-executed, and the fix appeared to
do nothing — the exact same failing verdict, the exact same z-statistics,
came back. Root cause: this suite's notebooks are built by a `build_ipynb_*.py`
script that reads the `.py` source and embeds it as a single static code
cell **at build time**. Editing the `.py` file after that point changes
nothing already baked into the `.ipynb` until the build script is re-run.

**Checklist, every time a `pipeline_*.py` file changes**:
1. Edit `pipeline_*.py`.
2. Re-run its `build_ipynb_*.py` to regenerate the `.ipynb` from the updated
   source.
3. Only THEN run `jupyter nbconvert --execute` — executing before step 2
   silently re-runs stale, already-embedded code and will not reflect the
   fix, with no error or warning that anything is wrong.
4. This does NOT apply to shared `src/` modules imported at runtime (e.g.
   `src/utils/stats_checks.py`) — those take effect on the next execution
   with no rebuild needed, because they are imported, not embedded. Know
   which kind of file you just edited.

## 2. `monotonic_within_noise()` has a documented input-ORDER contract — verify it, don't assume it

**What happened**: Problems 1 and 2 both fed this function their PD-risk-band
arrays in ascending-risk order (the natural order for a human-readable
report) without reversing them first. The function's docstring requires
descending order (index 0 = highest expected rate). Every adjacent-band
comparison was silently evaluated backwards, so the check reported a
"reversal" on every pair regardless of whether the real data was monotonic —
a real, previously-undetected bug that produced a false FAIL on the user's
real 307,511-row run, not a property of the data. See `CHANGELOG.md` [1.4.3].

**Checklist, every time `monotonic_within_noise()` (or any new ordering
check) is wired up to a new data source**: before the call, write out in a
comment which direction the array is ALREADY sorted in, and which direction
the metric is EXPECTED to move (increase or decrease) as you move through
that sort order. If those two don't match "index 0 = highest expected value",
reverse the array (`[::-1]`) immediately before the call — do not assume a
copy-pasted call site from another notebook already has the right
orientation for this one's data.

## 3. Statistical significance alone misbehaves at BOTH ends of the sample-size range

**What happened**: `monotonic_within_noise()`'s Bonferroni-corrected
two-proportion z-test is well-calibrated at fixture scale (~4,000 rows) but
becomes powerful enough at real production scale (300,000+ rows) to flag a
tiny, practically meaningless reversal as "significant" — a well-documented
statistical phenomenon (Cohen, 1994, "The Earth Is Round (p < .05)"), not a
bug in the test. Fixed in [1.4.3] by adding a real, disclosed minimum
practical-difference threshold alongside the significance test — a reversal
now only counts if it is BOTH statistically significant AND practically
material.

**Checklist, every time a new statistical significance test is introduced
in a future notebook**: consider explicitly what happens to that test's
power at real full-scale N (hundreds of thousands of rows) vs. this suite's
small synthetic fixture. If a "significant" result at real scale could be
practically trivial, add a documented, disclosed minimum-effect-size
threshold from the start — don't wait to discover it on the user's real run.

## 4. A hard-dependency check must compare the ACTUAL artifact contents, not just existence

**What happened**: Problem 1 (MP2 Notebook 01) correctly raises a loud,
actionable error when Notebook 01 (MP1)'s trained feature-set list doesn't
match what the current feature-engineering code produces — this caught a
real stale-bundle situation (the user's local champion model predated a
feature-engineering update) that would otherwise have silently scored PD
against the wrong feature set. This worked exactly as designed.

**Checklist, every time a new notebook adds a hard dependency on another
notebook's saved artifact (joblib bundle, CSV, JSON)**: don't just check the
file exists — compare whatever defines compatibility (feature list, column
set, schema version) between what was saved and what the current code would
produce right now, and fail loudly with the exact fix ("re-run Notebook X")
if they differ. A silent existence check would have let the mismatch through.

## 5. Real Monte Carlo / simulation throughput, measured on the user's real hardware

Recorded here (not fabricated — from the user's own pasted real-run output)
so a future notebook that needs Monte Carlo or other per-draw vectorized
simulation can forecast its own runtime before running it, rather than
surprising the user the way the original per-resample bootstrap did.

- Hardware: 16 logical / 8 physical cores, 31.3 GB RAM, WARP ceiling 15
  threads / 28.2 GB.
- MP2 Notebook 03 (Economic Capital): 70,000 total simulated draws (50,000
  main + 20,000 independent-reseed check) over 307,511 real applicants,
  vectorized in batches of 500 (one `scipy.stats.norm.cdf` call per batch,
  never per-draw or per-applicant) — **684.7 seconds (~11.4 minutes) real
  wall-clock, real RAM usage flat at ~24.3–24.4 GB throughout (no growth,
  comfortably under the 28.2 GB ceiling)**. That is roughly 31 million
  (draw × applicant) elements processed per second, single-effective-thread
  equivalent (`scipy.stats.norm.cdf` is not multi-threaded by default).
- Compare: the ORIGINAL per-resample bootstrap this suite replaced took
  ~3 hours and did not finish, on a smaller table, at fixture-comparable
  scale reasoning (see `BENCHMARKS.md` Notebook 05 entry) — vectorized
  batching is the reason this stayed in minutes, not hours, at real
  production scale.
- **Planning implication for Problems 4/5**: if a future notebook's
  simulation needs roughly `draws × applicants` on this order, expect
  minutes, not seconds, at real scale even though the fixture run (which is
  what gets verified in this cloud environment) will look instant — say so
  explicitly in that notebook's own header disclosure, the way Notebook 03's
  does, so the user isn't surprised mid-run the way they were the first
  time. Consider a lower default draw count with a documented
  `project_config.json` override for anyone who wants more precision at the
  cost of more wall-clock time, exactly as Notebook 03 already does
  (`"mc_draws"`).

## 6. Real cross-checks beat asserted correctness

**What worked well and should be repeated**: Problem 3's closed-form vs.
Monte Carlo cross-check (1.35% relative difference on the fixture, 1.62% on
real data — both well within the documented 10% tolerance) is a real,
independently-computed number that either confirms or contradicts another
part of the pipeline, not an assertion. Whenever two different notebooks (or
two sections of the same notebook) compute a version of the "same" real
quantity via genuinely different methods, cross-check them explicitly and
report the real relative difference — this is what caught nothing wrong here,
which is itself useful evidence, and would have caught something wrong if
there had been a bug.

## 7. Don't force a non-interactive matplotlib backend in a notebook that calls `plt.show()`

**What happened**: MP2 Notebook 06 was the only notebook in this suite that
explicitly called `matplotlib.use("Agg")` before importing `pyplot`, while
still calling `plt.show()` later. On the user's real run this produced a
`UserWarning: FigureCanvasAgg is non-interactive, and thus cannot be shown`
— harmless (the chart was already written to disk via `plt.savefig()`
before `plt.show()` ran, so the saved PNG was never affected), but a real,
avoidable inconsistency: every other notebook (01, 02, 03, 04, 05) just
does `import matplotlib.pyplot as plt` and lets Jupyter's own inline
backend handle `plt.show()` with no warning at all. Fixed in `CHANGELOG.md`
[1.4.9] by removing the explicit backend override.

**Checklist, every time a new notebook imports matplotlib**: don't call
`matplotlib.use(...)` at all unless there is a specific, disclosed reason
this notebook cannot run under Jupyter's default backend — match the
already-proven-clean import pattern every other notebook in this suite
uses (`import matplotlib.pyplot as plt`, nothing more, before any
`plt.show()` call).

## 8. Printed OUTPUT text is not runnable CODE — a real point of user confusion, not a suite bug

**What happened**: after a real run, the user pasted a printed `[ROLLUP]
Real baseline: ...` status line (output text, containing a dollar figure
like `$184,207,084,196`) into a Jupyter code cell and executed it, producing
`SyntaxError: leading zeros in decimal integer literals are not permitted`
— Python tried to parse the printed dollar amount's `084` as a numeric
literal. The notebook and its source code were never at fault; the actual
code cell (verified directly) contained only the correct
`print(f"[ROLLUP] Real baseline: {N_APPLICANTS:,} ...")` f-string template.

**Checklist, when a user reports a `SyntaxError` referencing a dollar
figure, a comma-formatted number, or prose-looking text**: before assuming
a code defect, check whether the reported error text matches this suite's
own PRINTED OUTPUT format (`[TAG] some sentence: real numbers.`) rather
than valid Python syntax — if so, the likely cause is output text pasted
into a code cell, not a bug in the delivered `.ipynb`. Verify by directly
inspecting the delivered notebook's actual code-cell source (not the
printed transcript) before concluding anything is broken.

## 9. Non-negotiable verification protocol (restated, not new — keep following it)

Fixture → real `jupyter nbconvert --execute` → 0 errors → outputs cleared +
`execution_count` cleared → `nbformat.validate()` → Playwright
network-blocked HTML dashboard check (0 console errors, 0 external
requests) → LibreOffice headless Excel recalculation check → only then
commit + deliver. Every notebook and every fix in this suite, including all
of the ones this file documents, went through every step of this before
being called done — no exceptions, no shortcuts, regardless of how
confident the fix looks in isolation.
