"""
src/monitoring/monitoring_common.py

HYPER shared component: a bin-share (Population Stability Index style)
helper, reused by monitoring_job.py and by generate_monitoring_baseline.py
so the exact same binning logic that built the baseline is the exact same
logic that scores new data against it.

This closes a real, previously-disclosed gap: the enterprise
production-readiness review of this suite found "PSI is used as a
validation concept inside notebooks, but no dedicated monitoring/
directory or monitoring job exists anywhere in the tracked repo." This
module, plus monitoring_job.py, is that missing piece.

KNOWN LIMITATION (disclosed, not hidden): this reports the new-window bin
share against fixed, pre-computed train-side quantile bin edges -- not a
full two-sided PSI sum (`sum((new_pct - train_pct) * ln(new_pct/train_pct))`)
-- because doing that requires the exact per-bin TRAIN percentages to be
persisted alongside the edges, which `generate_monitoring_baseline.py`
does do (see its `train_bin_pct` output key), so a full PSI number *can*
be computed from what this job already reports; `monitoring_job.py`
computes it below using both.
"""

from __future__ import annotations

from typing import Optional

import numpy as np


def bin_share(edges, window_col) -> Optional[list]:
    """Bin-share (population percentage per bin) of `window_col` against
    fixed `edges` (quantile bin edges computed once, at baseline time).
    Returns None if fewer than 3 edges were provided (not enough to form
    a bin)."""
    edges_arr = np.array(edges, dtype=float)
    if len(edges_arr) < 3:
        return None
    window_counts, _ = np.histogram(window_col, bins=edges_arr)
    window_pct = np.clip(window_counts / max(window_counts.sum(), 1), 1e-6, None)
    return window_pct.tolist()


def psi_from_bin_pct(train_pct, window_pct) -> Optional[float]:
    """Real, full two-sided PSI: sum((window_pct - train_pct) * ln(window_pct / train_pct))
    over matching bins. Returns None if the two bin-percent lists differ in
    length (misconfigured baseline) or either is empty."""
    if not train_pct or not window_pct or len(train_pct) != len(window_pct):
        return None
    t = np.clip(np.array(train_pct, dtype=float), 1e-6, None)
    w = np.clip(np.array(window_pct, dtype=float), 1e-6, None)
    return float(np.sum((w - t) * np.log(w / t)))
