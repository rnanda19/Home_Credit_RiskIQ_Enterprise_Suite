# Static Notebook Exports

Read-only, static HTML renders of all 31 real notebooks in this suite (the
25 problem notebooks + 5 Mega Project executive rollups + the suite-wide
rollup), one per notebook, mirroring the repo's own folder structure. A
casual visitor can open and read these directly on GitHub (or clone the
repo and open the file) without any risk of editing the source `.ipynb`
files in place.

## What these are, and what they aren't

**These are static exports of the notebooks' own real markdown and code
cells — not of computed results.** By this suite's own standing
convention (see `CONTRIBUTING.md` / `ROADMAP.md`), the `.ipynb` files
under each Mega Project's `notebooks/` folder are checked into git with
their **outputs cleared** — real execution only ever happens on your own
machine, against your own real, locally-downloaded Home Credit data, and
Claude working on this repo is under a standing rule to never execute a
notebook itself (see `ROADMAP.md`'s "execution boundary" note). So there
is nothing to "export the outputs of" here without actually running each
notebook — these HTML files render the same real business context,
methodology, and code every notebook carries in source form, exactly as
GitHub's own notebook viewer would, just as a locked, non-interactive
page.

**The real computed results already have their own, better home** —
don't look for them here:

- **Real, live dashboards** (`docs/dashboards/*.html`, rendered via
  GitHub Pages) — one per problem notebook plus each Mega Project's
  executive rollup and the suite-wide rollup. Linked from the top-level
  [`README.md`](../README.md#live-dashboards).
- **Real Word/Excel reports** (`sample_reports/*.docx` / `*.xlsx` per
  Mega Project) — generated from a real full-scale rerun on real data.

Regenerating this folder after re-running the notebooks is a static,
execution-free `jupyter nbconvert --to html` pass over each `.ipynb` —
safe to run any time (it renders whatever is already saved in the
notebook; it does not execute it):

```bash
jupyter nbconvert --to html --output-dir reports/<mega-project-folder> \
  <mega-project-folder>/notebooks/<notebook>.ipynb --output <notebook>
```
