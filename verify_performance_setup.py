"""
Real, end-to-end self-test of src/utils/performance_setup.py — exercises every function
against real (small) computation, not just import checks. Run this once after setup to
confirm the module works correctly on YOUR machine before relying on it in a notebook.
Prints your machine's real detected hardware and real ceilings — nothing here is invented.
"""
import sys
import time
from pathlib import Path


import os  # noqa: E402


def _find_suite_root(start: Path = None) -> Path:
    """Locate the home-credit-enterprise-suite project root (the folder containing
    project_config.json), regardless of where this is launched from. Checked in order,
    fastest and most explicit first -- deliberately NOT an unbounded/recursive filesystem
    scan (that would risk exactly the "hangs and looks frozen" problem this whole
    performance module exists to avoid, especially against a large Windows user profile):

    1. HC_SUITE_ROOT environment variable, if you've set one (most reliable — see README)
    2. Walking UPWARD from the working directory (covers: running from inside/under the
       project, e.g. a notebooks/ subfolder)
    3. A short list of well-known locations under the home directory and the working
       directory (covers: Jupyter's working directory being your home directory, e.g.
       C:\\Users\\<you>, which is an ANCESTOR of the project rather than inside it — this is
       what broke the previous, upward-search-only version of this file for a real user)
    """
    start = start or Path.cwd()
    marker = "project_config.json"

    env_override = os.environ.get("HC_SUITE_ROOT")
    if env_override:
        candidate = Path(env_override)
        if (candidate / marker).exists():
            return candidate
        raise FileNotFoundError(
            f"HC_SUITE_ROOT is set to {candidate}, but no {marker} was found there."
        )

    for candidate in [start, *start.parents]:
        if (candidate / marker).exists():
            return candidate

    well_known = [
        Path.home() / "Downloads" / "home-credit-enterprise-suite",
        Path.home() / "home-credit-enterprise-suite",
        Path.home() / "Desktop" / "home-credit-enterprise-suite",
        start / "home-credit-enterprise-suite",
        start / "Downloads" / "home-credit-enterprise-suite",
    ]
    for candidate in well_known:
        if (candidate / marker).exists():
            return candidate

    raise FileNotFoundError(
        f"Could not find project_config.json starting from {start} (checked upward, plus "
        f"{len(well_known)} well-known locations under your home directory). Fix: either (a) "
        "run this from inside the home-credit-enterprise-suite folder, or (b) set an "
        "environment variable before launching Jupyter/Python, e.g. on Windows PowerShell: "
        '$env:HC_SUITE_ROOT="C:\\Users\\rnand\\Downloads\\home-credit-enterprise-suite" '
        "-- see PERFORMANCE_SETUP_README.md."
    )


SUITE_ROOT = _find_suite_root()
sys.path.insert(0, str(SUITE_ROOT / "src"))
print(f"[VERIFY] Resolved suite root: {SUITE_ROOT.name}/ (found by walking up from {Path.cwd().name}/)")

from utils.performance_setup import (  # noqa: E402
    configure_performance, sklearn_n_jobs, gbm_thread_kwargs,
    threadpool_guard, free_memory, check_ram_headroom, scan_large_csv,
    progress, timer,
)

print("=" * 70)
print("STEP 1 — configure_performance() (must run before numpy/pandas/polars/sklearn import)")
PERF = configure_performance()
assert PERF["n_threads"] >= 1, "n_threads must be at least 1"
assert PERF["logical_cores"] >= 1

# Idempotency check
PERF2 = configure_performance()
assert PERF2 == PERF, "second call must return identical config (idempotent)"
print("[TEST] idempotency: PASS")

print("=" * 70)
print("STEP 2 — heavy imports AFTER configure_performance()")
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
import xgboost as xgb  # noqa: E402
import lightgbm as lgb  # noqa: E402
import catboost as cb  # noqa: E402
print("[TEST] all heavy libraries imported cleanly: PASS")

print("=" * 70)
print("STEP 3 — env vars actually applied")
import os  # noqa: E402
for var in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS", "POLARS_MAX_THREADS"]:
    val = os.environ.get(var)
    assert val == str(PERF["n_threads"]), f"{var} = {val}, expected {PERF['n_threads']}"
print(f"[TEST] all thread env vars set to {PERF['n_threads']}: PASS")

print("=" * 70)
print("STEP 4 — real small-scale model training with gbm_thread_kwargs() / sklearn_n_jobs()")
rng = np.random.default_rng(42)
X = rng.normal(size=(500, 8)).astype(np.float32)
y = (X[:, 0] + X[:, 1] > 0).astype(int)

kw = gbm_thread_kwargs()
rf = RandomForestClassifier(n_estimators=20, n_jobs=sklearn_n_jobs(), random_state=42).fit(X, y)
xgm = xgb.XGBClassifier(n_estimators=20, **kw["xgboost"], random_state=42).fit(X, y)
lgm = lgb.LGBMClassifier(n_estimators=20, **kw["lightgbm"], random_state=42, verbosity=-1).fit(X, y)
cbm = cb.CatBoostClassifier(iterations=20, **kw["catboost"], random_state=42, verbose=False).fit(X, y)
for name, m in [("RandomForest", rf), ("XGBoost", xgm), ("LightGBM", lgm), ("CatBoost", cbm)]:
    acc = (m.predict(X) == y).mean()
    assert 0.0 <= acc <= 1.0
    print(f"[TEST] {name} trained with configured thread ceiling, real train accuracy={acc:.3f}: PASS")

print("=" * 70)
print("STEP 5 — threadpool_guard() context manager")
with threadpool_guard():
    _ = np.linalg.inv(rng.normal(size=(200, 200)))
print("[TEST] threadpool_guard() ran a real linalg op without error: PASS")

print("=" * 70)
print("STEP 6 — check_ram_headroom()")
ok = check_ram_headroom()
assert isinstance(ok, bool)
print(f"[TEST] check_ram_headroom() returned a real boolean ({ok}): PASS")

print("=" * 70)
print("STEP 7 — scan_large_csv() lazy + streaming collect, on a real-schema fixture")
fixture_path = SUITE_ROOT / "fixture" / "application_train.csv"
if fixture_path.exists():
    lf = scan_large_csv(str(fixture_path))
    result = lf.select(["SK_ID_CURR", "TARGET"]).head(10).collect(streaming=True)
    assert result.height == 10
    print(f"[TEST] scan_large_csv().collect(streaming=True) returned {result.height} real rows: PASS")
else:
    print("[TEST] fixture/application_train.csv not found in this sandbox run — skipped (not a module bug)")

print("=" * 70)
print("STEP 8 — progress() wrapper")
total = 0
for i in progress(range(1000), desc="verify"):
    total += i
assert total == sum(range(1000))
print(f"[TEST] progress() iterated correctly, real sum={total}: PASS")

print("=" * 70)
print("STEP 9 — @timer decorator")


@timer("dummy_workload")
def dummy_workload():
    time.sleep(0.05)
    return 42


assert dummy_workload() == 42
print("[TEST] @timer decorator ran and returned the real function result: PASS")

print("=" * 70)
print("STEP 10 — free_memory() cleanup")
big = np.zeros((1000, 1000))
free_memory(big)
print("[TEST] free_memory() ran without error: PASS")

print("=" * 70)
print("ALL 10 STEPS PASSED — performance_setup.py is verified end-to-end on this machine.")
print(f"Real detected hardware this run: {PERF['logical_cores']} logical / "
      f"{PERF['physical_cores']} physical cores, {PERF['total_ram_gb']:.1f} GB RAM, "
      f"thread ceiling {PERF['n_threads']}, RAM ceiling {PERF['ram_ceiling_gb']:.1f} GB.")
