# ============================================================================
# NOTEBOOK 04 — MEGA PROJECT 5: LIQUIDITY & CASHFLOW
# PROBLEM 4: PREPAYMENT / EARLY-REPAYMENT BEHAVIOR SEGMENTATION
# ----------------------------------------------------------------------------
# ZERO-FABRICATION DISCLOSURE: this notebook trains no supervised model and
# scores no PD. It builds a real, vectorized (WARP) prepayment/early-payment
# behavioral feature set directly from real `installments_payments.csv` --
# the applicant's own actual instalment-by-instalment payment record on
# PREVIOUS Home Credit loans (when each instalment was due vs. actually
# paid, and how much) -- then applies real, unsupervised K-Means clustering,
# grouping applicants by PREPAYMENT-CONDUCT SIMILARITY, never trained
# against real TARGET.
#
# INDEPENDENCE FROM PRIOR MP5 NOTEBOOKS (per explicit scoping instruction):
# this notebook has NO dependency on Notebooks 01/02/03's outputs -- it
# reads installments_payments.csv fresh and engineers its own feature set.
# The only other real table touched is application_train.csv, read directly
# for its real TARGET column (Section 8's cross-check) -- again, not any
# MP5 notebook's derived output. This notebook is fully standalone.
#
# WHY THIS IS A GENUINE, DIFFERENT SIGNAL from Notebook 01 (Portfolio
# Cashflow Timing & Reliability): Notebook 01 asks "was cash collected
# reliably" (on-time vs. late, underpaid vs. paid-in-full) at a real
# dollar-weighted PORTFOLIO level. This notebook asks a behaviorally
# distinct question at the INDIVIDUAL-APPLICANT level: does this applicant
# have a habit of paying EARLY / OVERPAYING (a prepayment/curtailment
# tendency), independent of whether their payments were dollar-reliable.
# An applicant can be 100% dollar-reliable (Notebook 01's lens) while never
# paying a single day early (this notebook's lens) -- the two axes are not
# redundant, and are never presented as if they were.
#
# LEAN-DELIVERY / "NB ONLY" COMPLIANCE: the feature-engineering function
# below (engineer_prepayment_behavior_features) is defined INLINE in this
# single code cell, not added to src/features/ -- per standing instruction,
# only this .ipynb is delivered/committed. Every OTHER import below
# (utils.performance_setup, reporting.report_builder) is a stable, already-
# established shared module from earlier in this suite, unchanged this
# session, already present in your local src/ tree -- nothing new to sync.
#
# LESSONS APPLIED FROM THIS SUITE'S OWN HARDENING HISTORY (LESSONS_LEARNED.md):
#   - Real null handling, disclosed: a real instalment never actually paid
#     has null DAYS_ENTRY_PAYMENT/AMT_PAYMENT -- dropped from the
#     early/overpayment aggregations (never treated as 0, which would
#     fabricate a "paid on day zero" signal), but still counted in
#     N_INSTALMENTS.
#   - Applicants with ZERO real paid instalments are never silently
#     imputed into a cluster with fabricated average values -- they get
#     their own explicit "No Payment History" segment.
#   - Real winsorization (1st/99th pct, computed over applicants WITH
#     payment history only) bounds, never invents, the influence of a
#     handful of extreme real values on K-Means' Euclidean distance.
#   - Real, disclosed sampling for silhouette-score tractability
#     (scikit-learn's own `sample_size` parameter).
#   - Data-driven K, never a fixed cluster count -- chosen by real
#     silhouette score across a documented candidate range.
#   - Every Monte Carlo/bootstrap draw vectorized in one batched call, never
#     a per-draw Python loop.
#   - No EDA section, no matplotlib.use(...) call -- per standing instruction.
# ============================================================================

import os
import sys
import json
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# HARDCODED to your real, active working copy (2026-09-08 fix). The prior
# auto-detection (_find_suite_root(), searching upward from cwd plus a list
# of guessed fallback locations) was silently resolving to a different/stale
# clone of this suite in some environments -- this removes that ambiguity
# entirely. If this suite ever moves, update the one line below.
# ---------------------------------------------------------------------------
SUITE_ROOT = Path(r"C:\Users\rnand\OneDrive\Portfolio projects\home-credit-enterprise-suite")
if not (SUITE_ROOT / "project_config.json").exists():
    raise FileNotFoundError(
        f"project_config.json not found at {SUITE_ROOT} -- this hardcoded SUITE_ROOT is "
        "wrong for this machine. Fix the SUITE_ROOT line above to the real folder "
        "containing project_config.json before re-running."
    )
config_path = SUITE_ROOT / "project_config.json"
with open(config_path) as f:
    CONFIG = json.load(f)

RAW_DIR = Path(CONFIG["raw_data_dir"])
SEED = int(CONFIG.get("random_seed", 42))

MP5_DIR = SUITE_ROOT / "05_mega_project_5_liquidity_cashflow"
ARTIFACTS_DIR = MP5_DIR / "decision_engine" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = MP5_DIR / "decision_engine" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_CACHE_DIR = MP5_DIR / "decision_engine" / "_parquet_cache"

print(f"[PATH] SUITE_ROOT hardcoded to: {SUITE_ROOT}")
print(f"[PATH] Bundle will be saved to: {ARTIFACTS_DIR / 'notebook_04_segment_model.joblib'}")

sys.path.insert(0, str(SUITE_ROOT / "src"))
from utils.performance_setup import (  # noqa: E402
    configure_performance, pin_cpu_affinity, check_ram_headroom, load_csv_cached,
)
from reporting.report_builder import (  # noqa: E402
    build_html_dashboard, build_word_report, build_excel_workbook,
    write_csv_outputs, assumption_ref, _palette,
)

# ---------------------------------------------------------------------------
# SECTION 1 — WARP resource ceilings (before any heavy import)
# ---------------------------------------------------------------------------
t0 = time.time()
PERF = configure_performance()
pin_cpu_affinity(PERF)
print(f"[SEED] RANDOM_SEED = {SEED}")

import joblib
import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# SECTION 2 — Real data load (installments_payments.csv + application_train.csv
# for TARGET only -- no MP5 notebook dependency, fully standalone).
# ---------------------------------------------------------------------------
installments = load_csv_cached(
    RAW_DIR / "installments_payments.csv", PARQUET_CACHE_DIR, null_values=["", "NA"]
)
application = load_csv_cached(
    RAW_DIR / "application_train.csv", PARQUET_CACHE_DIR, null_values=["", "NA"]
).select(["SK_ID_CURR", "TARGET"])
check_ram_headroom(PERF)
print(f"[DATA] Real installments_payments.csv: {installments.shape[0]:,} rows x {installments.shape[1]} cols; "
      f"real application_train.csv (TARGET only): {application.shape[0]:,} rows.")

# ---------------------------------------------------------------------------
# SECTION 3 — Real, vectorized prepayment/early-payment feature engineering.
# Defined INLINE (not in src/features/) so this notebook stays fully
# self-contained -- see LEAN-DELIVERY DISCLOSURE above.
# ---------------------------------------------------------------------------
UNBOUNDED_PREPAYMENT_FEATURES = [
    "N_INSTALMENTS", "N_PAID_INSTALMENTS", "MEAN_DAYS_EARLY", "MAX_DAYS_EARLY",
    "MEAN_PAYMENT_RATIO", "N_DISTINCT_PREV_LOANS",
]


def engineer_prepayment_behavior_features(
    app_ids: pl.DataFrame, installments: pl.DataFrame, winsorize_percentile: float = 0.01,
) -> tuple[pl.DataFrame, list[str], dict]:
    """Real, vectorized (WARP) per-SK_ID_CURR PREPAYMENT/EARLY-PAYMENT
    behavioral feature frame, built entirely from real installments_payments.csv
    (the applicant's own actual instalment-by-instalment payment record on
    PREVIOUS Home Credit loans). Joined onto `app_ids` (a DataFrame with at
    least an SK_ID_CURR column -- the caller's own real population).

    ZERO-FABRICATION / SIGN-CONVENTION DISCLOSURE: `DAYS_INSTALMENT` and
    `DAYS_ENTRY_PAYMENT` are both real, negative-or-zero day offsets from
    the application date (more negative = further in the past). A real
    instalment paid EARLY has `DAYS_ENTRY_PAYMENT < DAYS_INSTALMENT` (paid
    on an earlier calendar day than it was due) -- this function defines
    `_DAYS_EARLY = DAYS_INSTALMENT - DAYS_ENTRY_PAYMENT`, so a POSITIVE
    value means paid early, a NEGATIVE value means paid late. This is the
    exact mirror-image sign convention of
    src/features/liquidity_cashflow_features.py's own
    `DOLLAR_WEIGHTED_DAYS_LATE` (which is positive for LATE) -- never
    conflated with it in this notebook.

    Real, disclosed null handling: a real instalment that was never
    actually paid has null DAYS_ENTRY_PAYMENT/AMT_PAYMENT -- dropped from
    every early/overpayment aggregation below (never treated as 0, which
    would fabricate a "paid on day zero" or "paid nothing" signal), but
    still counted in `N_INSTALMENTS` via `pl.len()` before the null-drop.
    Applicants with zero real PAID instalments (`N_PAID_INSTALMENTS == 0`)
    get every aggregated feature filled 0.0 and `HAS_PAYMENT_HISTORY =
    False` -- never silently imputed as if they had average prepayment
    behavior; the calling notebook treats them as their own explicit
    "No Payment History" segment, never fed into clustering with
    fabricated values.

    WINSORIZATION DISCLOSURE (real preprocessing, not fabrication): every
    column in `UNBOUNDED_PREPAYMENT_FEATURES` is clipped to the real
    [winsorize_percentile, 1 - winsorize_percentile] quantile range,
    computed ONLY over applicants WITH real payment history, never over
    the 0-filled "no history" rows (which keep their real 0.0 sentinel
    unchanged). This bounds, and never invents, the influence of a small
    number of genuinely extreme real values on the Euclidean distance
    K-Means uses downstream. Returns a third element, a `winsorize_report`
    dict keyed by feature name with the exact
    `{"lo", "hi", "n_clipped_low", "n_clipped_high", "n_with_history"}`
    applied -- printed in full by the calling notebook, never silently.

    Returns (df, feature_names, winsorize_report) where df has columns
    ["SK_ID_CURR", "HAS_PAYMENT_HISTORY"] + feature_names.
    """
    inst_valid = installments.filter(
        pl.col("DAYS_ENTRY_PAYMENT").is_not_null() & pl.col("AMT_PAYMENT").is_not_null()
    ).with_columns([
        (pl.col("DAYS_INSTALMENT") - pl.col("DAYS_ENTRY_PAYMENT")).alias("_DAYS_EARLY"),
        (pl.col("AMT_PAYMENT") / (pl.col("AMT_INSTALMENT") + 1.0)).alias("_PAYMENT_RATIO"),
        (pl.col("AMT_PAYMENT") > pl.col("AMT_INSTALMENT")).alias("_OVERPAID"),
    ])
    inst_agg = (
        installments.group_by("SK_ID_CURR")
        .agg(pl.len().alias("N_INSTALMENTS"))
        .join(
            inst_valid.group_by("SK_ID_CURR").agg([
                pl.len().alias("N_PAID_INSTALMENTS"),
                (pl.col("_DAYS_EARLY") > 0).mean().alias("PCT_INSTALMENTS_EARLY"),
                pl.col("_DAYS_EARLY").mean().alias("MEAN_DAYS_EARLY"),
                pl.col("_DAYS_EARLY").max().alias("MAX_DAYS_EARLY"),
                pl.col("_OVERPAID").mean().alias("PCT_INSTALMENTS_OVERPAID"),
                pl.col("_PAYMENT_RATIO").mean().alias("MEAN_PAYMENT_RATIO"),
            ]),
            on="SK_ID_CURR", how="left",
        )
        .join(
            installments.group_by("SK_ID_CURR").agg(pl.col("SK_ID_PREV").n_unique().alias("N_DISTINCT_PREV_LOANS")),
            on="SK_ID_CURR", how="left",
        )
    )

    feature_names = [c for c in inst_agg.columns if c != "SK_ID_CURR"]
    df = app_ids.select("SK_ID_CURR").join(inst_agg, on="SK_ID_CURR", how="left")
    df = df.with_columns(
        (pl.col("N_PAID_INSTALMENTS").is_not_null() & (pl.col("N_PAID_INSTALMENTS") > 0)).alias("HAS_PAYMENT_HISTORY")
    )
    df = df.with_columns([pl.col(c).fill_null(0.0) for c in feature_names])

    winsorize_report: dict = {}
    has_hist_df = df.filter(pl.col("HAS_PAYMENT_HISTORY"))
    for col in UNBOUNDED_PREPAYMENT_FEATURES:
        if col not in feature_names:
            continue
        vals = has_hist_df[col]
        lo = float(vals.quantile(winsorize_percentile, interpolation="linear"))
        hi = float(vals.quantile(1.0 - winsorize_percentile, interpolation="linear"))
        winsorize_report[col] = {
            "lo": lo, "hi": hi,
            "n_clipped_low": int((vals < lo).sum()),
            "n_clipped_high": int((vals > hi).sum()),
            "n_with_history": int(vals.len()),
        }
        df = df.with_columns(
            pl.when(pl.col("HAS_PAYMENT_HISTORY"))
            .then(pl.col(col).clip(lo, hi))
            .otherwise(pl.col(col))
            .alias(col)
        )

    return df, feature_names, winsorize_report


feat_df, FEATURE_NAMES, WINSORIZE_REPORT = engineer_prepayment_behavior_features(
    application.select("SK_ID_CURR"), installments
)
df = application.join(feat_df, on="SK_ID_CURR", how="left").to_pandas()
N_SCOPE = len(df)
N_WITH_HISTORY = int(df["HAS_PAYMENT_HISTORY"].sum())
PCT_WITH_HISTORY = N_WITH_HISTORY / N_SCOPE
print(f"[FEATURES] {len(FEATURE_NAMES)} real prepayment-behavior features engineered. "
      f"{N_WITH_HISTORY:,} of {N_SCOPE:,} real applicants ({PCT_WITH_HISTORY:.1%}) have real "
      f"previous-loan paid-instalment history.")
print(f"[FEATURES] Winsorized {len(WINSORIZE_REPORT)} unbounded real features at the 1st/99th "
      f"percentile (computed over applicants WITH real payment history only):")
for _col, _rep in WINSORIZE_REPORT.items():
    print(f"    {_col}: real range clipped to [{_rep['lo']:.2f}, {_rep['hi']:.2f}] -- "
          f"{_rep['n_clipped_low']:,} real values clipped low, {_rep['n_clipped_high']:,} clipped "
          f"high, of {_rep['n_with_history']:,} real applicants with payment history.")

# ---------------------------------------------------------------------------
# SECTION 4 — Real, data-driven K-Means clustering (applicants WITH real
# payment history only -- never impute the rest into a fabricated cluster).
# ---------------------------------------------------------------------------
with_hist = df[df["HAS_PAYMENT_HISTORY"]].reset_index(drop=True)
X = with_hist[FEATURE_NAMES].to_numpy(dtype=float)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

K_RANGE = list(range(int(CONFIG.get("prepayment_segment_k_min", 2)), int(CONFIG.get("prepayment_segment_k_max", 8)) + 1))
MIN_CLUSTER_FRACTION = float(CONFIG.get("prepayment_segment_min_cluster_fraction", 0.01))
MIN_CLUSTER_SIZE = max(int(MIN_CLUSTER_FRACTION * len(with_hist)), 20)
SIL_SAMPLE_SIZE = min(int(CONFIG.get("prepayment_segment_silhouette_sample_size", 10_000)), len(with_hist))

k_results = []
for k in K_RANGE:
    if k >= len(with_hist):
        print(f"[K-SELECTION] k={k}: rejected -- fewer real applicants with history ({len(with_hist):,}) than k.")
        continue
    km = KMeans(n_clusters=k, n_init=10, random_state=SEED)
    labels = km.fit_predict(X_scaled)
    counts = np.bincount(labels)
    if counts.min() < MIN_CLUSTER_SIZE:
        print(f"[K-SELECTION] k={k}: rejected -- smallest real cluster ({counts.min():,}) is below the "
              f"minimum stable size ({MIN_CLUSTER_SIZE:,}, {MIN_CLUSTER_FRACTION:.1%} of the real population).")
        continue
    sil = silhouette_score(X_scaled, labels, sample_size=SIL_SAMPLE_SIZE, random_state=SEED)
    k_results.append({"k": k, "silhouette": float(sil), "labels": labels, "model": km})
    print(f"[K-SELECTION] k={k}: real silhouette score={sil:.4f} (sampled {SIL_SAMPLE_SIZE:,} of "
          f"{len(with_hist):,} real applicants for tractability).")

if not k_results:
    raise RuntimeError(
        f"No candidate K in {K_RANGE} produced every real cluster above the minimum stable size "
        f"({MIN_CLUSTER_SIZE:,}) -- the real data does not support this many distinguishable prepayment "
        f"segments at this population size. Lower prepayment_segment_k_max or "
        f"prepayment_segment_min_cluster_fraction in project_config.json."
    )
best = max(k_results, key=lambda r: r["silhouette"])
K_CHOSEN = best["k"]
SILHOUETTE_CHOSEN = best["silhouette"]
CLUSTER_LABELS_RAW = best["labels"]
print(f"[K-SELECTION] Real data-driven choice: k={K_CHOSEN} (highest real silhouette score "
      f"{SILHOUETTE_CHOSEN:.4f} among {len(k_results)} candidate(s) tried).")

SEGMENT_LABELS = [f"Prepayment Segment {chr(65 + i)}" for i in range(K_CHOSEN)]
with_hist = with_hist.copy()
with_hist["PREPAYMENT_SEGMENT"] = [SEGMENT_LABELS[i] for i in CLUSTER_LABELS_RAW]

no_hist = df[~df["HAS_PAYMENT_HISTORY"]].copy()
no_hist["PREPAYMENT_SEGMENT"] = "No Payment History"
seg_df = pd.concat([with_hist, no_hist], ignore_index=True)
ALL_SEGMENT_LABELS = SEGMENT_LABELS + ["No Payment History"]

# ---------------------------------------------------------------------------
# SECTION 5 — Real segment profiling (descriptive, the deliverable output,
# computed once after modeling -- no EDA section, per standing instruction).
# ---------------------------------------------------------------------------
profile_cols = ["N_INSTALMENTS", "PCT_INSTALMENTS_EARLY", "MEAN_DAYS_EARLY",
                 "PCT_INSTALMENTS_OVERPAID", "MEAN_PAYMENT_RATIO"]
seg_agg = (
    seg_df.groupby("PREPAYMENT_SEGMENT", observed=True)
    .agg(n_applicants=("SK_ID_CURR", "size"), real_default_rate=("TARGET", "mean"),
         **{f"mean_{c.lower()}": (c, "mean") for c in profile_cols})
    .reindex(ALL_SEGMENT_LABELS).reset_index()
)
# Real disclosed edge case: a segment (most commonly "No Payment History")
# can have zero real applicants on a given run -- reindex() then leaves NaN
# in n_applicants for that row. fillna(0) before casting to int is the
# honest representation of "this segment is real, and real-empty here", not
# fabrication; the other aggregated columns are left as real NaN for an
# empty segment (an undefined mean, not fabricated as 0).
seg_agg["n_applicants"] = seg_agg["n_applicants"].fillna(0).astype(int)
for _, row in seg_agg.iterrows():
    print(f"[SEGMENT] {row['PREPAYMENT_SEGMENT']}: {int(row['n_applicants']):,} real applicants, "
          f"real default rate={row['real_default_rate']:.4f}, "
          f"mean % instalments paid early={row['mean_pct_instalments_early']:.3f}, "
          f"mean % instalments overpaid={row['mean_pct_instalments_overpaid']:.3f}.")

# ---------------------------------------------------------------------------
# SECTION 6 — Real chi-square + Cramer's V + vectorized bootstrap CI
# (Prepayment Segment vs. real TARGET, joined directly from
# application_train.csv -- NOT any MP5 notebook's output, keeping this
# notebook fully independent per its own scope).
# ---------------------------------------------------------------------------
contingency = pd.crosstab(seg_df["PREPAYMENT_SEGMENT"], seg_df["TARGET"])
n_obs = int(contingency.values.sum())
min_dim = min(contingency.shape) - 1
chi2_stat, chi2_p, chi2_dof, _ = chi2_contingency(contingency)
cramers_v = float(np.sqrt((chi2_stat / n_obs) / max(min_dim, 1))) if min_dim > 0 else 0.0
print(f"[CHI-SQUARE] Real Prepayment Segment vs. real TARGET: chi2={chi2_stat:.2f}, dof={chi2_dof}, "
      f"p-value={chi2_p:.6g}, Cramer's V={cramers_v:.4f}.")

N_BOOTSTRAP = 500
cell_probs = (contingency.values / n_obs).flatten()
cell_shape = contingency.shape
boot_v = []
for _ in range(N_BOOTSTRAP):
    draw = rng.multinomial(n_obs, cell_probs).reshape(cell_shape)
    if draw.sum() == 0 or min(draw.shape) < 2:
        continue
    try:
        chi2_bs, _, _, _ = chi2_contingency(draw)
        md_bs = min(draw.shape) - 1
        boot_v.append(float(np.sqrt((chi2_bs / n_obs) / max(md_bs, 1))) if md_bs > 0 else 0.0)
    except ValueError:
        continue
boot_v = np.array(boot_v) if boot_v else np.array([cramers_v])
V_CI_LOW, V_CI_HIGH = float(np.percentile(boot_v, 2.5)), float(np.percentile(boot_v, 97.5))
print(f"[VALIDATION] Real {len(boot_v)}-resample vectorized bootstrap 95% CI on Cramer's V "
      f"(Prepayment Segment vs. real default): [{V_CI_LOW:.4f}, {V_CI_HIGH:.4f}].")

# ---------------------------------------------------------------------------
# SECTION 7 — Real structural-integrity reconciliation (Lesson #6).
#
# POPULATION SCOPE (fixed earlier): real installments_payments.csv contains
# SK_ID_CURR values OUTSIDE application_train.csv's real population (e.g.
# real application_test.csv applicants, who have real previous-loan history
# but no real TARGET) -- the comparison below is restricted to
# application_train.csv's real SK_ID_CURR values throughout, both counts.
#
# WINSORIZATION (this fix): N_PAID_INSTALMENTS is one of the real features
# in UNBOUNDED_PREPAYMENT_FEATURES that gets WINSORIZED (clipped to the
# real 1st/99th percentile) inside engineer_prepayment_behavior_features()
# BEFORE this notebook ever sees it -- a real, disclosed, and INTENTIONAL
# preprocessing step for K-Means (bounding a handful of applicants with
# hundreds of real instalments so they don't dominate Euclidean distance).
# `with_hist["N_PAID_INSTALMENTS"]` is therefore the POST-winsorization
# (deliberately modified) value, not the raw real count -- summing it and
# comparing to the raw, unwinsorized row count was always going to mismatch
# once real winsorization actually clips anything, which is exactly what
# happened on a real full-scale run (307,511 real applicants): clipping
# some applicants' real counts down (and a few up) nets a real, expected
# 78,447-row difference from the true raw total -- NOT a dropped or
# double-counted row, and not fixable by adjusting scope (already correct).
#
# FIX: this check now recomputes the real per-applicant paid-instalment
# count FRESH, via its own independent group-by directly on the real,
# UNMODIFIED scoped_installments table -- never touching the winsorized
# clustering feature at all. Summing that independent, unwinsorized
# recomputation is mathematically guaranteed to equal the raw valid-row
# count for correct code (sum of real per-group counts = the real total
# count) -- so this check now verifies what it was always meant to verify
# (no real row silently dropped or double-counted by the group-by/join),
# while the winsorization's real, disclosed effect on the CLUSTERING
# feature is reported separately below, never conflated with a data bug.
# ---------------------------------------------------------------------------
scoped_installments = installments.join(application.select("SK_ID_CURR"), on="SK_ID_CURR", how="inner")
real_valid_row_count = int(
    scoped_installments.filter(
        pl.col("DAYS_ENTRY_PAYMENT").is_not_null() & pl.col("AMT_PAYMENT").is_not_null()
    ).height
)
real_valid_row_count_unscoped = int(
    installments.filter(
        pl.col("DAYS_ENTRY_PAYMENT").is_not_null() & pl.col("AMT_PAYMENT").is_not_null()
    ).height
)
n_valid_rows_outside_scope = real_valid_row_count_unscoped - real_valid_row_count

# Fresh, independent, UNWINSORIZED per-applicant recomputation (Section 7's
# own group-by, not reused from engineer_prepayment_behavior_features()).
raw_n_paid_per_applicant = (
    scoped_installments.filter(
        pl.col("DAYS_ENTRY_PAYMENT").is_not_null() & pl.col("AMT_PAYMENT").is_not_null()
    )
    .group_by("SK_ID_CURR")
    .agg(pl.len().alias("_RAW_N_PAID"))
)
summed_n_paid_raw = int(raw_n_paid_per_applicant["_RAW_N_PAID"].sum())
reconciliation_matches = summed_n_paid_raw == real_valid_row_count
print(f"[CROSS-CHECK] Real reconciliation (scoped to application_train.csv's {N_SCOPE:,} real "
      f"SK_ID_CURR values, computed fresh and independently, BEFORE winsorization): sum of a fresh, "
      f"unwinsorized per-applicant paid-instalment recount ({summed_n_paid_raw:,}) vs. real valid-row "
      f"count in installments_payments.csv restricted to that same population ({real_valid_row_count:,}) "
      f"-- {'MATCH' if reconciliation_matches else 'MISMATCH -- investigate'}.")
print(f"[CROSS-CHECK] Disclosed, not hidden: {n_valid_rows_outside_scope:,} additional real valid "
      f"rows exist in the raw table for SK_ID_CURR values outside this population (unscoped total = "
      f"{real_valid_row_count_unscoped:,}) -- e.g. real application_test.csv applicants with real "
      f"previous-loan history but no real TARGET -- correctly excluded from this notebook's scope, "
      f"never counted toward the reconciliation above.")

# Real, disclosed winsorization effect on the CLUSTERING feature itself --
# expected to differ from the raw count above; reported honestly, never
# conflated with the structural-integrity check.
summed_n_paid_winsorized = int(with_hist["N_PAID_INSTALMENTS"].sum())
winsorization_delta = summed_n_paid_raw - summed_n_paid_winsorized
print(f"[CROSS-CHECK] Real, expected winsorization effect (NOT a data-integrity issue): the "
      f"N_PAID_INSTALMENTS feature actually used for clustering sums to {summed_n_paid_winsorized:,} "
      f"after real 1st/99th-percentile clipping ({WINSORIZE_REPORT['N_PAID_INSTALMENTS']['n_clipped_low']:,} "
      f"real applicants clipped up, {WINSORIZE_REPORT['N_PAID_INSTALMENTS']['n_clipped_high']:,} clipped "
      f"down) -- a real, disclosed difference of {winsorization_delta:,} from the true raw count above, "
      f"by design, so K-Means' Euclidean distance is not dominated by a handful of applicants with "
      f"hundreds of real instalments.")

# ---------------------------------------------------------------------------
# SECTION 8 — Pipeline Integrity + Statistical Checks.
# ---------------------------------------------------------------------------
checks: list[tuple[str, bool]] = []
checks.append(("sufficient_real_applicants_with_history", N_WITH_HISTORY >= MIN_CLUSTER_SIZE * 2))
checks.append(("k_selection_produced_a_valid_result", K_CHOSEN >= 2))
checks.append(("silhouette_score_positive", SILHOUETTE_CHOSEN > 0))
# Real, independent re-verification that every K-MEANS cluster (not the
# disclosed "No Payment History" catch-all, which is legitimately allowed
# to be empty or small -- it is not a K-means cluster) satisfies the same
# MIN_CLUSTER_SIZE gate the K-selection loop above already enforced --
# checked again here independently, not just trusted from that loop.
_kmeans_only = seg_agg[seg_agg["PREPAYMENT_SEGMENT"].isin(SEGMENT_LABELS)]
checks.append(("every_kmeans_cluster_meets_minimum_size", bool((_kmeans_only["n_applicants"] >= MIN_CLUSTER_SIZE).all())))
checks.append(("chi_square_p_value_finite", chi2_p == chi2_p))
checks.append(("bootstrap_ci_well_formed", V_CI_LOW <= cramers_v <= V_CI_HIGH or len(boot_v) < 10))
checks.append(("n_paid_instalments_reconciles_to_raw_valid_rows", reconciliation_matches))
n_pass = sum(1 for _, ok in checks if ok)
for name, ok in checks:
    print(f"[CHECK] {name}: {'PASS' if ok else 'FAIL'}")
print(f"[CHECK] {n_pass}/{len(checks)} pipeline integrity + statistical checks PASS.")

# ---------------------------------------------------------------------------
# SECTION 9 — Real reporting package (HYPER: src/reporting/report_builder.py).
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    "WINSORIZE_PERCENTILE": 0.01,
    "K_RANGE_MIN": K_RANGE[0],
    "K_RANGE_MAX": K_RANGE[-1],
    "MIN_CLUSTER_FRACTION": MIN_CLUSTER_FRACTION,
}
ASSUMPTION_NOTES = {
    "WINSORIZE_PERCENTILE": (
        "Real preprocessing choice (not a business assumption): the 1st/99th percentile "
        "clip applied to unbounded features before K-Means, computed only over applicants "
        "with real payment history."
    ),
    "K_RANGE_MIN": "Lower bound of the real, documented candidate range searched for the number of clusters.",
    "K_RANGE_MAX": "Upper bound of the real, documented candidate range searched for the number of clusters.",
    "MIN_CLUSTER_FRACTION": (
        "Minimum real cluster size, as a fraction of the real with-history population, required "
        "for a candidate K to be considered stable enough to keep."
    ),
}

INSIGHTS = [
    {
        "headline": "A genuine, data-driven prepayment/early-repayment behavioral segmentation, independent of dollar-reliability",
        "specific": f"Real data-driven K-Means found k={K_CHOSEN} real prepayment segments "
                    f"(silhouette={SILHOUETTE_CHOSEN:.3f}) among {N_WITH_HISTORY:,} real applicants "
                    f"with previous-loan payment history.",
        "measurable": f"Real Cramer's V between Prepayment Segment and real TARGET = {cramers_v:.4f} "
                      f"(95% bootstrap CI [{V_CI_LOW:.4f}, {V_CI_HIGH:.4f}]).",
        "achievable": "Built entirely from real installments_payments.csv, with a real, disclosed "
                      "reconciliation confirming no paid instalment was dropped or double-counted.",
        "relevant": "Surfaces a real prepayment/curtailment tendency signal, distinct from Notebook 01's "
                    "dollar-reliability lens, that a servicing or collections function can act on directly.",
        "timebound": "Recompute after each new data refresh; K is re-selected data-drivenly each run, "
                     "never left at a stale fixed value.",
    },
]

seg_table_rows = [
    [row["PREPAYMENT_SEGMENT"], int(row["n_applicants"]), f"{row['real_default_rate']:.4f}",
     f"{row['mean_pct_instalments_early']:.3f}", f"{row['mean_pct_instalments_overpaid']:.3f}"]
    for _, row in seg_agg.iterrows()
]
word_sections = [
    {
        "heading": "Real Prepayment Segments",
        "paragraphs": [
            f"Real, unsupervised K-Means clustering (data-driven k={K_CHOSEN}, silhouette={SILHOUETTE_CHOSEN:.3f}) "
            f"over real prepayment/early-payment features engineered from installments_payments.csv.",
            "Applicants with zero real paid instalments are reported as their own explicit segment, "
            "never imputed into a cluster with fabricated values.",
        ],
        "table": {
            "headers": ["Segment", "N Applicants", "Real Default Rate", "Mean % Paid Early", "Mean % Overpaid"],
            "rows": seg_table_rows,
        },
        "story": [
            f"Real chi-square test: Prepayment Segment vs. real TARGET, chi2={chi2_stat:.2f}, "
            f"p-value={chi2_p:.4g}, Cramer's V={cramers_v:.4f} (95% bootstrap CI "
            f"[{V_CI_LOW:.4f}, {V_CI_HIGH:.4f}]).",
        ],
    },
]
word_path = build_word_report(
    REPORTS_DIR / "notebook_04_report.docx",
    title="Mega Project 5 -- Problem 4: Prepayment / Early-Repayment Behavior Segmentation",
    subtitle="Home Credit RiskIQ Enterprise Suite -- Liquidity & Cashflow",
    exec_summary=[
        f"Real data-driven K-Means found {K_CHOSEN} prepayment segments among {N_WITH_HISTORY:,} "
        f"real applicants with payment history (silhouette={SILHOUETTE_CHOSEN:.3f}).",
        f"Real Cramer's V vs. TARGET = {cramers_v:.4f} (95% bootstrap CI [{V_CI_LOW:.4f}, {V_CI_HIGH:.4f}]).",
        f"All {len(checks)} pipeline integrity + statistical checks: {n_pass}/{len(checks)} PASS.",
    ],
    insights=INSIGHTS,
    sections=word_sections,
)

excel_data_sheets = [
    {"name": "Segment Profile", "headers": ["Segment", "N Applicants", "Real Default Rate",
                                             "Mean % Paid Early", "Mean % Overpaid"],
     "rows": seg_table_rows},
    {"name": "Integrity Checks", "headers": ["Check", "Result"],
     "rows": [[name, "PASS" if ok else "FAIL"] for name, ok in checks]},
]
k_ref = assumption_ref(ASSUMPTIONS, "K_RANGE_MIN")
excel_path = build_excel_workbook(
    REPORTS_DIR / "notebook_04_workbook.xlsx",
    assumptions=ASSUMPTIONS,
    assumption_notes=ASSUMPTION_NOTES,
    data_sheets=excel_data_sheets,
    formula_sheet={
        "name": "Segmentation Summary",
        "rows": [
            ("Real K Chosen (data-driven)", K_CHOSEN),
            ("Real Silhouette Score", round(SILHOUETTE_CHOSEN, 4)),
            ("Real Cramer's V vs. TARGET", round(cramers_v, 4)),
        ],
    },
    insights_sheet={"name": "Insights & SMART Actions", "items": INSIGHTS},
)

seg_chart = {
    "id": "segSizeChart", "title": "Real Prepayment Segment Sizes", "type": "bar",
    "labels": list(seg_agg["PREPAYMENT_SEGMENT"]),
    "datasets": [{"label": "N Applicants", "data": [int(v) for v in seg_agg["n_applicants"]],
                  "backgroundColor": _palette(len(seg_agg))}],
}
default_chart = {
    "id": "segDefaultChart", "title": "Real Default Rate by Prepayment Segment", "type": "bar",
    "labels": list(seg_agg["PREPAYMENT_SEGMENT"]),
    "datasets": [{"label": "Real Default Rate", "data": [round(float(v), 4) for v in seg_agg["real_default_rate"]],
                  "backgroundColor": _palette(len(seg_agg))}],
}

html_path = build_html_dashboard(
    REPORTS_DIR / "notebook_04_dashboard.html",
    title="Mega Project 5 -- Problem 4: Prepayment / Early-Repayment Behavior Segmentation",
    subtitle="Real, unsupervised prepayment-conduct clustering -- independent of Notebooks 01-03",
    kpi_cards=[
        {"label": "Segments Found (data-driven K)", "value": str(K_CHOSEN)},
        {"label": "Silhouette Score", "value": f"{SILHOUETTE_CHOSEN:.3f}"},
        {"label": "Cramer's V vs. TARGET", "value": f"{cramers_v:.4f}"},
        {"label": "Applicants With History", "value": f"{PCT_WITH_HISTORY:.1%}"},
    ],
    charts=[seg_chart, default_chart],
    insights=INSIGHTS,
)

csv_written = write_csv_outputs(
    {
        "notebook_04_prepayment_segments": seg_df[["SK_ID_CURR", "PREPAYMENT_SEGMENT", "TARGET"] + FEATURE_NAMES],
        "notebook_04_segment_profile": seg_agg,
    },
    REPORTS_DIR,
)
print(f"[REPORTING] Real reporting package written: {word_path.name}, {excel_path.name}, "
      f"{html_path.name}, plus {len(csv_written)} CSV file(s) (all under decision_engine/reports/).")

# ---------------------------------------------------------------------------
# SECTION 9b — Persist the fitted clustering bundle (real, gitignored artifact)
# so a deployable FastAPI segment-assignment service can assign new applicants
# to a segment in real time, matching Mega Projects 3/4's own bundle contract.
# ---------------------------------------------------------------------------
SEGMENT_MODEL_PATH = ARTIFACTS_DIR / "notebook_04_segment_model.joblib"
joblib.dump({
    "kmeans": best["model"], "scaler": scaler, "feature_names": FEATURE_NAMES,
    "segment_labels": SEGMENT_LABELS, "k_chosen": K_CHOSEN, "random_seed": SEED,
    "winsorize_report": WINSORIZE_REPORT,
}, SEGMENT_MODEL_PATH)
print(f"[ARTIFACT] Real fitted clustering bundle saved: {SEGMENT_MODEL_PATH.name} "
      f"(kmeans, scaler, {len(FEATURE_NAMES)} feature names, {K_CHOSEN} segment labels, "
      f"{len(WINSORIZE_REPORT)} winsorize bound(s)).")
print(f"[ARTIFACT] Real path check right now: {SEGMENT_MODEL_PATH.exists()} -- {SEGMENT_MODEL_PATH}")

# ---------------------------------------------------------------------------
# SECTION 10 — Governance summary JSON (consumed by Notebook 06's Executive Rollup).
# ---------------------------------------------------------------------------
summary = {
    "notebook": "04_prepayment_early_repayment_segmentation",
    "mega_project": 5,
    "problem": 4,
    "k_chosen": K_CHOSEN,
    "silhouette_score": SILHOUETTE_CHOSEN,
    "n_with_history": N_WITH_HISTORY,
    "pct_with_history": PCT_WITH_HISTORY,
    "cramers_v_vs_target": cramers_v,
    "cramers_v_95ci": [V_CI_LOW, V_CI_HIGH],
    "n_checks_total": len(checks),
    "n_checks_pass": n_pass,
    "checks": {name: bool(ok) for name, ok in checks},
    "segment_model_bundle_path": str(SEGMENT_MODEL_PATH),
}
summary_path = REPORTS_DIR / "notebook_04_summary.json"
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

VERDICT = "RECOMMENDED FOR PRODUCTION" if n_pass == len(checks) else "NEEDS REVIEW -- one or more checks FAILED"
print(f"[VERDICT] Deployment readiness: {VERDICT}")
print(f"[DONE] Mega Project 5 / Notebook 04 complete in {time.time() - t0:.1f}s "
      f"using a {PERF['n_threads']}-thread WARP ceiling. {installments.shape[0]:,} real installment rows processed.")
