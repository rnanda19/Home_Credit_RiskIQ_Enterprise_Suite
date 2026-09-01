# WARP Performance & Resource Governance Setup

Concrete, importable implementation of the suite's standing WARP resource-ceiling rule
(max 90% RAM, max 95% CPU threads, never 100%), built to stop the real, common cause of a
laptop feeling "frozen" during a notebook run: several fast libraries (NumPy/OpenBLAS,
scikit-learn, XGBoost, LightGBM, CatBoost, Polars) each independently grabbing every CPU
thread at once, rather than any single step actually being slow.

## What's in this delivery

| File | Purpose |
|---|---|
| `src/utils/performance_setup.py` | The module itself — hardware detection, one shared thread ceiling applied to every library, RAM headroom checks, streaming CSV loads for the suite's largest files, memory cleanup, progress bars, timing. |
| `verify_performance_setup.py` | A real, 10-step, end-to-end self-test (not a syntax check) — run once to confirm the module works correctly on your machine before relying on it. |
| `requirements-performance.txt` | The specific libraries this module uses: `threadpoolctl`, `numba`, `numexpr`, `bottleneck`, `tqdm`, plus the ones already in `requirements.txt` (`psutil`, `joblib`, `polars`). |

## Adoption policy — from Problem 2 onward

Notebooks 01–05 (Mega Project 1: Underwriting & Decisioning) were already built and delivered
before this module existed, and are **not** being retrofitted — they already ran cleanly on a
schema-matched fixture with 0 errors, and reopening delivered, verified notebooks to change
their internals is exactly the kind of rework this suite's standing rules try to avoid.

Every notebook from Mega Project 2 (Problem 2) onward will start with this as its first
executable lines, before any other import:

```python
import sys
from pathlib import Path
SUITE_ROOT = config_path.parent   # same resolution pattern every notebook already uses
sys.path.insert(0, str(SUITE_ROOT / "src"))
from utils.performance_setup import (
    configure_performance, sklearn_n_jobs, gbm_thread_kwargs,
    check_ram_headroom, scan_large_csv, progress, free_memory,
)

PERF = configure_performance()   # MUST be called before numpy/pandas/polars/sklearn import
```

Then, wherever a notebook already does this:

```python
RandomForestClassifier(n_jobs=-1, ...)
xgb.XGBClassifier(...)                    # thread count left on default
```

it instead does this:

```python
RandomForestClassifier(n_jobs=sklearn_n_jobs(PERF), ...)
xgb.XGBClassifier(**gbm_thread_kwargs(PERF)["xgboost"], ...)
```

And wherever a notebook loads one of this suite's largest real files —
`bureau_balance.csv` (27.3M rows), `installments_payments.csv` (13.6M rows),
`POS_CASH_balance.csv` (10.0M rows), `credit_card_balance.csv` (3.8M rows) — it uses
`scan_large_csv(path).select([...]).collect(streaming=True)` instead of `pl.read_csv(path)`,
so the file is processed lazily rather than fully materialized in RAM the instant it loads.

## Run the self-test once

```bash
cd home-credit-enterprise-suite
pip install -r requirements-performance.txt
python verify_performance_setup.py
```

This prints your **real** detected hardware (logical/physical cores, total RAM) and the real
thread/RAM ceilings computed for your machine — nothing here is a canned or invented number.
All 10 steps must print `PASS`.

You can also run it inside Jupyter (paste the cell, or `%run verify_performance_setup.py`).
It resolves the project root in this order, so it works no matter where Jupyter's working
directory actually is:

1. An `HC_SUITE_ROOT` environment variable, if you set one — the most reliable option if
   your setup is unusual. On Windows, before launching Jupyter:
   ```powershell
   $env:HC_SUITE_ROOT="C:\Users\rnand\Downloads\home-credit-enterprise-suite"
   jupyter lab
   ```
2. Walking **upward** from the working directory — covers running from inside the project
   (e.g. a `notebooks/` subfolder).
3. A short, fixed list of well-known locations under your home directory (`~/Downloads/home-credit-enterprise-suite`, `~/home-credit-enterprise-suite`, `~/Desktop/home-credit-enterprise-suite`) — covers Jupyter's default working directory being your home folder itself (e.g. `C:\Users\rnand`), which is an *ancestor* of the project rather than inside it, so an upward-only search can't find it. This is a fixed handful of direct existence checks, not a recursive scan of your whole filesystem — it will never hang looking for it.

(Two earlier versions of this file assumed the working directory always *was* the project
root, then assumed it was always somewhere *inside* the project — both real bugs, now fixed;
see the Evidence Ledger discussion in this session for the failures that led here.)

## Two things this module deliberately does NOT do

- **It does not claim a speedup percentage.** Claude never runs this suite on your real
  hardware or your real data, so any specific "N% faster" figure would be invented. Time
  your own real runs (the `@timer` decorator and `verify_performance_setup.py`'s own printed
  timings give you real numbers) if you want to compare before/after.
- **It does not raise thread/process priority above normal.** Some "performance" guides
  suggest setting a Python process to high/realtime OS priority. That can starve the OS
  itself of CPU time and cause the exact freezing this module exists to prevent, so it is
  intentionally left out.

## Two non-code things worth knowing on a Ryzen laptop

- **Windows power plan**: under Settings → Power & battery, a plan other than "Best
  Performance" (or Balanced with an aggressive battery saver) can itself throttle CPU clock
  speed regardless of anything Python does. Worth checking once before a long real-data run,
  especially on battery power.
- **Sustained thermal load**: a laptop chassis has less cooling headroom than a desktop: the
  95%-not-100% thread ceiling in this module already leaves the CPU some room to breathe, but
  a multi-hour real run (e.g. the full 6-model benchmark across all 18 problems) will still
  run warm. That's expected, not a bug — the ceiling exists precisely so it stays "warm and
  responsive" rather than "pinned at 100% and stuck."
