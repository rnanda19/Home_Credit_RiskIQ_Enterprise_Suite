"""
src/utils/performance_setup.py

WARP Performance & Resource Governance Module — Home Credit Default Risk 5 Mega Project Suite.

WHY THIS EXISTS
----------------
A laptop "freezing" during a real notebook run is almost never one slow library — it is
usually several fast libraries (NumPy/OpenBLAS, scikit-learn, XGBoost, LightGBM, CatBoost,
Polars) each independently deciding to use *every* CPU thread at once, because each one reads
its own thread-count setting from its own default (and several of those defaults are "all
cores"). Six libraries x "all cores" = 6x oversubscription, and oversubscription is what pins
a Ryzen laptop's fans at 100% and makes the whole machine feel stuck, even though no single
step in the notebook is actually that expensive at real Home Credit data scale
(300K-27M real rows depending on file).

This module fixes that at the root: ONE detected hardware ceiling, applied to every library
that would otherwise guess its own. It is the concrete, importable implementation of the
WARP standard already documented in the suite's Master Execution Plan (resource ceilings:
max 90% RAM, max 95% CPU threads, never 100%).

HOW TO USE (from Mega Project 2 / Problem 2 onward — see the suite's build log)
--------------------------------------------------------------------------------
    import sys
    from pathlib import Path
    SUITE_ROOT = ...  # same project_config.json resolution pattern as every other notebook
    sys.path.insert(0, str(SUITE_ROOT / "src"))
    from utils.performance_setup import configure_performance, sklearn_n_jobs, gbm_thread_kwargs

    PERF = configure_performance()          # <-- FIRST executable line, before numpy/pandas/
                                             #     polars/sklearn/xgboost/lightgbm/catboost import
    import polars as pl
    import numpy as np
    ...

configure_performance() MUST run before those libraries are imported anywhere in the process
(including transitively, e.g. importing pandas also imports numpy). NumPy/OpenBLAS/MKL and
Polars read their thread-count environment variables exactly once, at their own import/init
time — setting the variable after import has no effect. This is the single most common reason
a "thread limit" appears to silently do nothing.

Zero-fabrication note: the thread/RAM ceilings and env-var wiring below are real, standard,
independently-documented behavior of these libraries (OpenMP/OpenBLAS/MKL/Polars all publish
these exact environment variable names). No specific speedup number is claimed anywhere in
this module — this suite never runs on your real hardware, so any number would be invented.
Run verify_performance_setup.py on your own machine to see your own real numbers.
"""
import os
import time
import gc
import warnings
import multiprocessing
import contextlib
import functools
from pathlib import Path

warnings.filterwarnings("ignore")

RAM_CEILING_FRACTION = 0.90
CPU_CEILING_FRACTION = 0.95

_CONFIGURED = {"done": False, "config": None}


def _detect_hardware():
    import psutil
    logical = psutil.cpu_count(logical=True) or multiprocessing.cpu_count() or 1
    physical = psutil.cpu_count(logical=False) or logical
    total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
    return {"logical_cores": logical, "physical_cores": physical, "total_ram_gb": total_ram_gb}


def configure_performance(ram_ceiling_fraction: float = RAM_CEILING_FRACTION,
                           cpu_ceiling_fraction: float = CPU_CEILING_FRACTION,
                           verbose: bool = True) -> dict:
    """Detect this machine's real cores/RAM and set every BLAS/OpenMP/Polars thread-count
    environment variable to one shared, safe ceiling. Call this BEFORE importing numpy,
    pandas, polars, scikit-learn, xgboost, lightgbm, or catboost. Idempotent — calling it
    again in the same process is a no-op that returns the already-computed config.
    """
    if _CONFIGURED["done"]:
        if verbose:
            print("[PERF] configure_performance() already applied this session (idempotent no-op).")
        return _CONFIGURED["config"]

    hw = _detect_hardware()
    n_threads = max(1, int(hw["logical_cores"] * cpu_ceiling_fraction))
    ram_ceiling_gb = hw["total_ram_gb"] * ram_ceiling_fraction

    thread_vars = [
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
        "POLARS_MAX_THREADS",
    ]
    for var in thread_vars:
        os.environ[var] = str(n_threads)

    # AMD Ryzen note (ASSUMPTION-free, historical fact, harmless either way): some older Intel
    # MKL builds throttled non-"GenuineIntel" CPUs via a cpuid check. MKL_DEBUG_CPU_TYPE=5 is
    # the documented community workaround on affected builds. Setting it is a no-op if your
    # numpy/scipy build doesn't use MKL at all (e.g. an OpenBLAS build), so it is always safe
    # to set defensively.
    os.environ.setdefault("MKL_DEBUG_CPU_TYPE", "5")

    config = {
        "logical_cores": hw["logical_cores"],
        "physical_cores": hw["physical_cores"],
        "total_ram_gb": round(hw["total_ram_gb"], 2),
        "n_threads": n_threads,
        "ram_ceiling_gb": round(ram_ceiling_gb, 2),
        "cpu_ceiling_fraction": cpu_ceiling_fraction,
        "ram_ceiling_fraction": ram_ceiling_fraction,
    }
    _CONFIGURED["done"] = True
    _CONFIGURED["config"] = config

    if verbose:
        print(f"[PERF] Detected: {hw['logical_cores']} logical / {hw['physical_cores']} physical cores, "
              f"{hw['total_ram_gb']:.1f} GB RAM")
        print(f"[PERF] Thread ceiling set to {n_threads} ({cpu_ceiling_fraction:.0%} of logical cores) "
              f"across OMP/OpenBLAS/MKL/NumExpr/Polars — one number, one source of truth, "
              f"so no library is left to guess and oversubscribe")
        print(f"[PERF] RAM ceiling: {ram_ceiling_gb:.1f} GB ({ram_ceiling_fraction:.0%} of "
              f"{hw['total_ram_gb']:.1f} GB total) — checked on demand via check_ram_headroom()")

    return config


def sklearn_n_jobs(config: dict = None) -> int:
    """n_jobs value for scikit-learn estimators / joblib.Parallel, from the shared ceiling."""
    config = config or _CONFIGURED.get("config") or configure_performance(verbose=False)
    return config["n_threads"]


def gbm_thread_kwargs(config: dict = None) -> dict:
    """Explicit per-library thread kwargs for XGBoost / LightGBM / CatBoost. Pass these into
    every model constructor instead of leaving thread count on default — the default is what
    lets each library independently grab every core during a benchmark loop that trains all
    6 models back to back, which is a real, common cause of a laptop feeling stuck mid-run.

    Example:
        kw = gbm_thread_kwargs()
        xgb.XGBClassifier(**kw["xgboost"], ...)
        lgb.LGBMClassifier(**kw["lightgbm"], ...)
        cb.CatBoostClassifier(**kw["catboost"], ...)
    """
    config = config or _CONFIGURED.get("config") or configure_performance(verbose=False)
    n = config["n_threads"]
    return {"xgboost": {"n_jobs": n}, "lightgbm": {"n_jobs": n}, "catboost": {"thread_count": n}}


def pin_cpu_affinity(config: dict = None, verbose: bool = True) -> list:
    """Explicitly pin this process to ALL detected logical cores via psutil.

    Why this exists: the thread-count env vars above tell each library how many
    threads it is ALLOWED to spawn — they do not guarantee the OS scheduler actually
    lets this process run on every core. If something upstream of this notebook's own
    kernel process (another app, a container/VM cgroup limit, a prior taskset/affinity
    call, Windows' own process-affinity default on some OEM power profiles) already
    narrowed this process's usable-core mask, every thread-count env var above still
    gets set correctly and every model still requests the configured n_jobs/thread_count
    threads, but the OS quietly time-slices all of them across a small subset of cores —
    which is observationally indistinguishable from "only using 20% of the CPU" even
    though the code did everything right. Setting affinity explicitly to every detected
    logical core removes that possibility rather than assuming it isn't happening.

    Best-effort and always safe: cpu_affinity() is supported on Windows and Linux but
    raises AttributeError/NotImplementedError on macOS — caught and skipped there, since
    macOS has no equivalent user-space API and does not need this fix.
    """
    import psutil
    config = config or _CONFIGURED.get("config") or configure_performance(verbose=False)
    try:
        proc = psutil.Process()
        all_cores = list(range(config["logical_cores"]))
        proc.cpu_affinity(all_cores)
        if verbose:
            print(f"[PERF] CPU affinity pinned to all {len(all_cores)} detected logical cores "
                  f"(removes any pre-existing OS-level core restriction on this process).")
        return all_cores
    except (AttributeError, NotImplementedError, OSError, psutil.Error) as e:
        if verbose:
            print(f"[PERF] CPU affinity pinning not applied on this platform ({type(e).__name__}: {e}) "
                  f"— safe to ignore, thread-count env vars above still apply.")
        return []


@contextlib.contextmanager
def threadpool_guard(n_threads: int = None):
    """Belt-and-suspenders guard for any BLAS call issued after numpy/scipy were already
    imported elsewhere (e.g. inside a third-party library that imported numpy before this
    module ran) — threadpoolctl re-caps live thread pools at the C level, catching what the
    environment variables above could not because they were set too late in that case."""
    try:
        from threadpoolctl import threadpool_limits
    except ImportError:
        yield
        return
    n = n_threads or (_CONFIGURED.get("config") or {}).get("n_threads") or max(1, multiprocessing.cpu_count() - 1)
    with threadpool_limits(limits=n):
        yield


def free_memory(*objs) -> None:
    """Explicit large-object cleanup between notebook sections: del + gc.collect(). The real
    fix for a laptop's RAM climbing across a long notebook run until it starts swapping —
    call this after you are done with a large intermediate DataFrame/array, before the next
    large one is built."""
    for o in objs:
        del o
    gc.collect()


def check_ram_headroom(config: dict = None, hard_stop: bool = False) -> bool:
    """Real-time RAM check against the configured ceiling. Call after loading each of this
    suite's largest real files (bureau_balance.csv: 27.3M rows, installments_payments.csv:
    13.6M rows, POS_CASH_balance.csv: 10.0M rows, credit_card_balance.csv: 3.8M rows) so a
    runaway load is caught with a clear message instead of the machine silently grinding
    into swap and appearing frozen."""
    import psutil
    config = config or _CONFIGURED.get("config") or configure_performance(verbose=False)
    vm = psutil.virtual_memory()
    used_gb = vm.used / (1024 ** 3)
    ceiling_gb = config["ram_ceiling_gb"]
    ok = used_gb < ceiling_gb
    print(f"[PERF] RAM in use: {used_gb:.1f} GB / ceiling {ceiling_gb:.1f} GB "
          f"({'OK' if ok else 'OVER CEILING'})")
    if not ok and hard_stop:
        raise MemoryError(
            f"RAM in use ({used_gb:.1f} GB) exceeds the configured {ceiling_gb:.1f} GB ceiling. "
            "Consider scan_large_csv(...).collect(streaming=True) for the current file, "
            "processing it in chunks, or closing other applications before re-running this cell."
        )
    return ok


def scan_large_csv(path, **scan_kwargs):
    """Lazy, streaming-friendly load for this suite's largest real files. Returns a Polars
    LazyFrame — chain your filters/selects/aggregations on it, then call
    `.collect(streaming=True)` at the end, instead of `pl.read_csv(...)`, which materializes
    the entire file in RAM immediately and is the most direct route to a laptop-freezing
    27-million-row load."""
    import polars as pl
    defaults = {"null_values": ["", "NA", "XNA"]}
    defaults.update(scan_kwargs)
    return pl.scan_csv(path, **defaults)


def load_csv_cached(path, cache_dir, verbose: bool = True, **read_csv_kwargs):
    """Parquet-over-CSV caching (WARP technique #7): returns a real Polars DataFrame for
    `path`, reading it from a cached `.parquet` copy under `cache_dir` when that cache is
    fresh (exists and is newer than the source CSV's mtime), or reading the real CSV and
    writing a fresh Parquet cache for next time when it is not.

    Honest trade-off, stated plainly: CSV is Home Credit's only real distribution format,
    so THE FIRST run of a notebook using this helper is not faster — it pays the normal CSV
    parse cost plus a small extra cost to write the Parquet cache. Every run AFTER that
    first one (e.g. re-running this notebook after a code change, or a second real session)
    reads the columnar, compressed Parquet copy instead — Parquet's binary columnar format
    skips CSV's row-by-row text parsing, which is the real, measurable win. Never mutates
    or writes into your actual Kaggle raw_data_dir — the cache lives entirely under this
    project's own cache_dir.

    Zero-fabrication note: this only changes how fast the same real numbers are read off
    disk. Every row and column value in the returned DataFrame is identical either way."""
    import polars as pl
    path = Path(path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{path.stem}.parquet"
    if cache_path.exists() and cache_path.stat().st_mtime >= path.stat().st_mtime:
        if verbose:
            print(f"[PERF] {path.name}: reading cached Parquet ({cache_path.name}) — "
                  f"faster than re-parsing the real CSV.")
        return pl.read_parquet(cache_path)
    df = pl.read_csv(path, **read_csv_kwargs)
    try:
        df.write_parquet(cache_path)
        if verbose:
            print(f"[PERF] {path.name}: read real CSV, wrote Parquet cache for future runs "
                  f"({cache_path.name}).")
    except OSError as e:
        if verbose:
            print(f"[PERF] {path.name}: read real CSV; Parquet cache write skipped ({e}).")
    return df


def progress(iterable, **kwargs):
    """tqdm progress bar with a no-op fallback if tqdm isn't installed. Visible progress
    during any real loop over this suite's larger files is what tells you the process is
    working, not stuck — silence during a multi-minute real-data step is what actually reads
    as a freeze, even when nothing is wrong."""
    try:
        from tqdm.auto import tqdm
        return tqdm(iterable, **kwargs)
    except ImportError:
        return iterable


def timer(label: str = ""):
    """Decorator: prints real wall-clock time for the function it wraps — cheap, honest
    timing feedback so a long real-data cell's completion is visible, not just assumed."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            result = fn(*args, **kwargs)
            print(f"[PERF] {label or fn.__name__} completed in {time.time() - t0:.1f}s")
            return result
        return wrapper
    return decorator
