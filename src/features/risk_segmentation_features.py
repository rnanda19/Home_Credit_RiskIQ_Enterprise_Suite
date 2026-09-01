"""
src/features/risk_segmentation_features.py

Shared feature-engineering module for Mega Project 3 (Risk Segmentation). Built
once (HYPER standing rule), imported by every MP3 notebook that needs a genuinely
new real behavioral feature space to segment applicants by -- deliberately kept
separate from src/features/credit_default_features.py (Mega Project 1's PD feature
set) so each MP3 problem builds a real segmentation axis independent of, not a
relabeling of, whatever already feeds the champion PD model.

ZERO-FABRICATION / OVERLAP DISCLOSURE (read before using): Mega Project 1's
champion model already includes 7 real bureau/bureau_balance summary features
(BUREAU_CNT_CREDITS, BUREAU_CNT_ACTIVE, BUREAU_AMT_CREDIT_SUM_TOTAL,
BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL, BUREAU_MAX_DAYS_OVERDUE, BUREAU_TOTAL_DPD_MONTHS,
BUREAU_DEBT_TO_CREDIT_RATIO -- see src/features/applicant_credit_history_features.py
`engineer_bureau_history_features()`). `engineer_bureau_behavior_features()` below
does NOT just relabel those same 7 numbers: it builds a richer, more granular real
feature set (credit-type mix, overdue AMOUNT not just DPD-month count, credit-limit
usage, recency, distinct-type count, worst real bureau_balance status severity) AND
applies a genuinely different MECHANISM (unsupervised clustering by behavioral
similarity, never trained against real TARGET) rather than the supervised
classification MP1's model uses. Both facts -- richer features AND a different
mechanism -- are what make this a real, non-redundant segmentation axis, and both
are disclosed again in the calling notebook's own model card.

`engineer_repayment_behavior_features()` (added for Notebook 03) is a third,
independent real feature space: the applicant's own actual instalment-by-
instalment payment conduct on PREVIOUS HOME CREDIT loans (real
`installments_payments.csv` lateness/payment-ratio) plus real
`POS_CASH_balance.csv` days-past-due tracking -- distinct from both Problem 1
(PD level) and Problem 2 (external bureau behavior at OTHER institutions).

`engineer_revolving_credit_utilization_features()` (added for Notebook 04) is
a fourth, independent real feature space built entirely from real
`credit_card_balance.csv` -- the applicant's own real revolving/credit-card
usage PATTERN on PREVIOUS Home Credit loans (real month-by-month utilization,
minimum-payment behavior, and cash-advance frequency), distinct from Problem
1 (PD level), Problem 2 (external bureau behavior), and Problem 3 (previous
INSTALMENT-LOAN repayment conduct -- installments_payments.csv /
POS_CASH_balance.csv, neither of which this function reads).
ZERO-FABRICATION / OVERLAP DISCLOSURE: Mega Project 1's champion model
already includes 8 real credit_card_balance.csv SUM-based features
(CC_N_OWN, CC_SUM_UTILIZATION_OWN, CC_SUM_BALANCE_OWN, CC_SUM_SK_DPD_OWN,
CC_N_TOT, CC_SUM_UTILIZATION_TOT, CC_SUM_BALANCE_TOT, CC_SUM_SK_DPD_TOT --
see src/features/applicant_credit_history_features.py). This function does
NOT just relabel those same numbers: it builds a richer real feature set
(utilization DISTRIBUTION -- mean, max, and % of months near-limit, not just
a running sum; real minimum-payment-only behavior; real cash-advance
frequency and share of drawings) AND applies a genuinely different MECHANISM
(unsupervised clustering by usage-pattern similarity, never trained against
real TARGET) -- the same "richer features AND a different mechanism"
argument already established for Problem 2's bureau function above.
"""
import polars as pl

# Ordinal severity for real bureau_balance STATUS codes (Home Credit's own coding):
# "C" = closed (no delinquency), "X" = status unknown, "0" = no DPD this month,
# "1".."5" = increasing real days-past-due buckets. C and X carry no real
# delinquency signal and are mapped to 0 (not dropped -- these are real, valid
# monthly records, just not delinquent ones).
_STATUS_SEVERITY = {"C": 0, "X": 0, "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}


def engineer_bureau_behavior_features(
    app_ids: pl.DataFrame, bureau: pl.DataFrame, bureau_balance: pl.DataFrame,
) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP) per-SK_ID_CURR credit-bureau BEHAVIORAL feature
    frame, joined onto `app_ids` (a DataFrame with at least an SK_ID_CURR column
    -- the caller's own real population of interest, e.g. Mega Project 3 /
    Notebook 01's real tiered applicants). Applicants with zero real bureau.csv
    rows get every feature filled 0/null and `HAS_BUREAU_HISTORY = False` -- never
    silently imputed as if they had average behavior; the calling notebook is
    expected to treat them as their own explicit segment, not to feed them into
    clustering with fabricated values.

    Returns (df, feature_names) where df has columns
    ["SK_ID_CURR", "HAS_BUREAU_HISTORY"] + feature_names.
    """
    # Real bureau_balance monthly-status severity, aggregated to one row per
    # SK_ID_BUREAU (a single credit line at another institution), then joined
    # onto bureau.csv before rolling up to SK_ID_CURR -- same two-step pattern
    # already used (and leakage-checked) by applicant_credit_history_features.py.
    bb_severity = bureau_balance.with_columns(
        pl.col("STATUS").cast(pl.Utf8).replace_strict(_STATUS_SEVERITY, default=0).alias("_SEVERITY")
    )
    bb_agg = (
        bb_severity.group_by("SK_ID_BUREAU")
        .agg([
            pl.len().alias("_BB_N_MONTHS"),
            pl.col("_SEVERITY").max().alias("_BB_WORST_SEVERITY"),
            (pl.col("_SEVERITY") > 0).sum().alias("_BB_N_DPD_MONTHS"),
        ])
    )
    bureau_with_bb = bureau.join(bb_agg, on="SK_ID_BUREAU", how="left").with_columns([
        pl.col("_BB_N_MONTHS").fill_null(0),
        pl.col("_BB_WORST_SEVERITY").fill_null(0),
        pl.col("_BB_N_DPD_MONTHS").fill_null(0),
    ])

    # Real credit-type mix: share of each applicant's real bureau credits
    # belonging to the most common real CREDIT_TYPE categories in THIS run's
    # data (computed dynamically from real data, never a hardcoded assumed
    # category list, so this stays correct on the fixture and on real data
    # even if category spellings/frequencies differ).
    top_types = (
        bureau.group_by("CREDIT_TYPE").agg(pl.len().alias("_n")).sort("_n", descending=True)
        .head(4)["CREDIT_TYPE"].to_list()
    )
    type_share_exprs = [
        (pl.col("CREDIT_TYPE") == t).mean().alias(f"PCT_TYPE_{i}") for i, t in enumerate(top_types)
    ]

    bureau_agg = (
        bureau_with_bb.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("N_BUREAU_CREDITS"),
            (pl.col("CREDIT_ACTIVE") == "Active").mean().alias("PCT_ACTIVE_CREDITS"),
            (pl.col("AMT_CREDIT_SUM_OVERDUE") > 0).mean().alias("PCT_CREDITS_WITH_OVERDUE"),
            pl.col("AMT_CREDIT_SUM_OVERDUE").sum().alias("TOTAL_AMT_OVERDUE"),
            pl.col("CREDIT_DAY_OVERDUE").max().alias("MAX_DAYS_OVERDUE"),
            pl.col("CNT_CREDIT_PROLONG").sum().alias("CNT_CREDIT_PROLONGED_TOTAL"),
            pl.col("AMT_CREDIT_SUM").sum().alias("_AMT_CREDIT_SUM_TOTAL"),
            pl.col("AMT_CREDIT_SUM_DEBT").sum().alias("_AMT_CREDIT_SUM_DEBT_TOTAL"),
            pl.col("AMT_CREDIT_SUM_LIMIT").sum().alias("AMT_CREDIT_SUM_LIMIT_TOTAL"),
            (pl.col("DAYS_CREDIT").abs() / 365.25).mean().alias("MEAN_YEARS_SINCE_CREDIT_OPENED"),
            pl.col("CREDIT_TYPE").n_unique().alias("N_DISTINCT_CREDIT_TYPES"),
            pl.col("_BB_WORST_SEVERITY").max().alias("WORST_BUREAU_BALANCE_STATUS"),
            (pl.col("_BB_N_DPD_MONTHS").sum() / (pl.col("_BB_N_MONTHS").sum() + 1.0)).alias("PCT_DPD_MONTHS"),
            *type_share_exprs,
        ])
        .with_columns(
            (pl.col("_AMT_CREDIT_SUM_DEBT_TOTAL") / (pl.col("_AMT_CREDIT_SUM_TOTAL") + 1.0))
            .alias("DEBT_TO_CREDIT_RATIO")
        )
        .drop(["_AMT_CREDIT_SUM_TOTAL", "_AMT_CREDIT_SUM_DEBT_TOTAL"])
    )

    feature_names = [c for c in bureau_agg.columns if c != "SK_ID_CURR"]
    df = app_ids.select("SK_ID_CURR").join(bureau_agg, on="SK_ID_CURR", how="left")
    df = df.with_columns(pl.col("N_BUREAU_CREDITS").is_not_null().alias("HAS_BUREAU_HISTORY"))
    df = df.with_columns([pl.col(c).fill_null(0.0) for c in feature_names])
    return df, feature_names


# Real features with no natural upper bound (unlike the four 0-1 real ratio
# features below, which need no clipping). A small number of genuinely
# extreme real values in these columns -- e.g. an instalment paid thousands
# of real days late, or a real AMT_PAYMENT/AMT_INSTALMENT ratio inflated by a
# near-zero real denominator -- can dominate Euclidean distance once
# StandardScaler standardizes everything to comparable variance, causing
# K-Means to isolate a handful of real outliers as their own tiny cluster
# instead of finding the real population's genuine behavioral groups. See
# `engineer_repayment_behavior_features()`'s WINSORIZATION DISCLOSURE below.
UNBOUNDED_REPAYMENT_FEATURES = [
    "N_INSTALMENTS", "MEAN_DAYS_LATE", "MAX_DAYS_LATE", "MEAN_PAYMENT_RATIO",
    "N_DISTINCT_PREV_LOANS", "N_POS_CASH_MONTHS", "MEAN_SK_DPD", "MAX_SK_DPD",
    "MEAN_SK_DPD_DEF",
]


def engineer_repayment_behavior_features(
    app_ids: pl.DataFrame, installments: pl.DataFrame, pos_cash: pl.DataFrame,
    winsorize_percentile: float = 0.01,
) -> tuple[pl.DataFrame, list[str], dict]:
    """Real, vectorized (WARP) per-SK_ID_CURR REPAYMENT-DISCIPLINE behavioral
    feature frame -- built for Mega Project 3 / Notebook 03 (Repayment Behavior
    Segmentation) -- from real `installments_payments.csv` (the applicant's own
    actual instalment-by-instalment payment record on PREVIOUS Home Credit loans:
    when each instalment was due vs. when it was actually paid, and how much) and
    real `POS_CASH_balance.csv` (real month-by-month days-past-due tracking on
    previous point-of-sale / cash loans). Joined onto `app_ids` (a DataFrame with
    at least an SK_ID_CURR column -- the caller's own real population of
    interest, e.g. Mega Project 3 / Notebook 01's real tiered applicants).

    ZERO-FABRICATION / OVERLAP DISCLOSURE: this is a genuinely different real
    signal from both Problem 1 (PD-level tiers) and Problem 2 (external bureau
    behavior at OTHER institutions) -- this feature set is built entirely from
    the applicant's own real repayment conduct on PREVIOUS HOME CREDIT loans,
    which `engineer_bureau_behavior_features()` above never touches (that
    function reads external bureau.csv/bureau_balance.csv only). Applicants
    with zero real `installments_payments.csv` rows get every feature filled
    0/null and `HAS_REPAYMENT_HISTORY = False` -- never silently imputed as if
    they had average payment behavior; the calling notebook is expected to
    treat them as their own explicit segment, not to feed them into clustering
    with fabricated values. Real `POS_CASH_balance.csv` features are joined in
    as additional, optional context (filled 0 when absent for an applicant who
    has real instalment history but no real POS/cash-loan monthly tracking --
    e.g. an applicant whose previous loans were consumer loans, not POS/cash)
    -- presence of REPAYMENT history is judged by `installments_payments.csv`
    alone, the more directly relevant of the two real tables to "repayment
    behavior."

    Real, disclosed null handling (matters more on your real data than on this
    suite's fixture, which happens to have none): `DAYS_ENTRY_PAYMENT` and
    `AMT_PAYMENT` are null on a real instalment that was never actually paid
    (still outstanding) -- both are dropped from the lateness/payment-ratio
    aggregations (never treated as 0, which would fabricate a "paid on day
    zero" or "paid nothing" signal) but still counted in `N_INSTALMENTS` via
    `pl.len()` before the null-drop, so a real applicant with many real unpaid
    instalments is not silently hidden from the "how many total" feature.

    WINSORIZATION DISCLOSURE (real preprocessing, not fabrication): after the
    real features below are engineered, every column in
    `UNBOUNDED_REPAYMENT_FEATURES` is clipped to the real
    [winsorize_percentile, 1 - winsorize_percentile] quantile range --
    computed ONLY over applicants WITH real repayment history, never over
    the 0-filled "no history" rows, and never applied to those rows either
    (they keep their real 0.0 sentinel unchanged). This BOUNDS, and never
    INVENTS, the influence of a small number of genuinely extreme real
    values on the Euclidean distance K-Means uses downstream -- every
    clipped value is still a real value that occurred in the real data,
    just capped to a real, disclosed quantile of the real with-history
    population's own distribution, exactly the way a real analyst would
    winsorize before a distance-based method. Returns a third element, a
    `winsorize_report` dict keyed by feature name with the exact
    `{"lo", "hi", "n_clipped_low", "n_clipped_high", "n_with_history"}`
    applied -- the calling notebook prints this in full, never silently.

    Returns (df, feature_names, winsorize_report) where df has columns
    ["SK_ID_CURR", "HAS_REPAYMENT_HISTORY"] + feature_names.
    """
    # --- Real instalments_payments.csv: real per-instalment lateness (positive
    # DAYS_LATE = paid after the real due date; negative = paid early) and real
    # payment-completeness ratio (AMT_PAYMENT / AMT_INSTALMENT). Guards a
    # divide-by-zero on a real AMT_INSTALMENT of exactly 0 (a real, if rare,
    # case -- e.g. a zero-amount instalment record) with +1.0 in the
    # denominator, the same disclosed pattern already used for
    # DEBT_TO_CREDIT_RATIO above.
    inst_valid = installments.filter(
        pl.col("DAYS_ENTRY_PAYMENT").is_not_null() & pl.col("AMT_PAYMENT").is_not_null()
    ).with_columns([
        (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT")).alias("_DAYS_LATE"),
        (pl.col("AMT_PAYMENT") / (pl.col("AMT_INSTALMENT") + 1.0)).alias("_PAYMENT_RATIO"),
    ])
    inst_agg = (
        installments.group_by("SK_ID_CURR")
        .agg(pl.len().alias("N_INSTALMENTS"))
        .join(
            inst_valid.group_by("SK_ID_CURR").agg([
                (pl.col("_DAYS_LATE") > 0).mean().alias("PCT_INSTALMENTS_LATE"),
                pl.col("_DAYS_LATE").mean().alias("MEAN_DAYS_LATE"),
                pl.col("_DAYS_LATE").max().alias("MAX_DAYS_LATE"),
                pl.col("_PAYMENT_RATIO").mean().alias("MEAN_PAYMENT_RATIO"),
                (pl.col("_PAYMENT_RATIO") < 0.99).mean().alias("PCT_INSTALMENTS_UNDERPAID"),
            ]),
            on="SK_ID_CURR", how="left",
        )
        .join(
            installments.group_by("SK_ID_CURR").agg(pl.col("SK_ID_PREV").n_unique().alias("N_DISTINCT_PREV_LOANS")),
            on="SK_ID_CURR", how="left",
        )
    )

    # --- Real POS_CASH_balance.csv: real month-by-month days-past-due tracking
    # plus real contract-status mix (share of real months Active/Completed).
    pos_agg = (
        pos_cash.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("N_POS_CASH_MONTHS"),
            pl.col("SK_DPD").mean().alias("MEAN_SK_DPD"),
            pl.col("SK_DPD").max().alias("MAX_SK_DPD"),
            pl.col("SK_DPD_DEF").mean().alias("MEAN_SK_DPD_DEF"),
            (pl.col("NAME_CONTRACT_STATUS") == "Active").mean().alias("PCT_MONTHS_ACTIVE"),
            (pl.col("NAME_CONTRACT_STATUS") == "Completed").mean().alias("PCT_MONTHS_COMPLETED"),
        ])
    )

    combined = inst_agg.join(pos_agg, on="SK_ID_CURR", how="left")
    feature_names = [c for c in combined.columns if c != "SK_ID_CURR"]
    df = app_ids.select("SK_ID_CURR").join(combined, on="SK_ID_CURR", how="left")
    df = df.with_columns(pl.col("N_INSTALMENTS").is_not_null().alias("HAS_REPAYMENT_HISTORY"))
    df = df.with_columns([pl.col(c).fill_null(0.0) for c in feature_names])

    # --- Real winsorization: computed and applied only over applicants WITH
    # real repayment history (see WINSORIZATION DISCLOSURE above). Applicants
    # with no real repayment history keep their real 0.0 sentinel untouched.
    winsorize_report: dict = {}
    has_hist_df = df.filter(pl.col("HAS_REPAYMENT_HISTORY"))
    for col in UNBOUNDED_REPAYMENT_FEATURES:
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
            pl.when(pl.col("HAS_REPAYMENT_HISTORY"))
            .then(pl.col(col).clip(lo, hi))
            .otherwise(pl.col(col))
            .alias(col)
        )

    return df, feature_names, winsorize_report


# Real features with no natural upper bound for the revolving-credit space
# (unlike the four 0-1 real "PCT_MONTHS_..." indicator features below, which
# are means of a boolean and so are 0-1 bounded by construction, needing no
# clipping). Winsorized from the start (LESSONS_LEARNED.md -- Notebook 03's
# real-data incident where leaving these unclipped let a handful of extreme
# real values dominate Euclidean distance and caused K-Means to isolate them
# as their own tiny outlier cluster).
UNBOUNDED_REVOLVING_FEATURES = [
    "N_CC_MONTHS", "N_DISTINCT_PREV_CC_LOANS", "MEAN_UTILIZATION",
    "MAX_UTILIZATION", "MEAN_MIN_PAYMENT_RATIO", "MEAN_ATM_DRAWINGS_SHARE",
    "MEAN_SK_DPD", "MAX_SK_DPD", "MEAN_SK_DPD_DEF",
]


def engineer_revolving_credit_utilization_features(
    app_ids: pl.DataFrame, credit_card: pl.DataFrame, winsorize_percentile: float = 0.01,
) -> tuple[pl.DataFrame, list[str], dict]:
    """Real, vectorized (WARP) per-SK_ID_CURR REVOLVING-CREDIT-UTILIZATION
    behavioral feature frame -- built for Mega Project 3 / Notebook 04
    (Revolving Credit Utilization Segmentation) -- from real
    `credit_card_balance.csv` (the applicant's own real month-by-month
    credit-card balance, credit limit, drawings, and minimum-payment record
    on PREVIOUS Home Credit revolving loans). Joined onto `app_ids` (the
    caller's own real population of interest, e.g. Mega Project 3 /
    Notebook 01's real tiered applicants). Real Kaggle
    `credit_card_balance.csv` only has rows for applicants whose previous
    loans included a real revolving/credit-card product -- most applicants
    have none, and get `HAS_REVOLVING_HISTORY = False` with every feature
    filled 0/null, never silently imputed as if they had average usage; the
    calling notebook is expected to treat them as their own explicit
    segment.

    ZERO-FABRICATION / OVERLAP DISCLOSURE: see this module's own top-of-file
    disclosure for how this differs from Mega Project 1's existing
    credit-card SUM features (richer distribution + a different, unsupervised
    mechanism) and from Problems 1-3 (distinct real signal, distinct table).

    Real, disclosed null handling: real `AMT_INST_MIN_REGULARITY` is null on
    a real month with no minimum payment due (e.g. a real zero-balance
    month) -- dropped from the minimum-payment-ratio and
    minimum-payment-only aggregations (never treated as 0, which would
    fabricate a "no minimum due" signal as "underpaid"), but every real
    month is still counted in `N_CC_MONTHS` regardless.

    WINSORIZATION DISCLOSURE (real preprocessing, not fabrication, applied
    from the start per Notebook 03's real-data lesson -- see
    LESSONS_LEARNED.md): every column in `UNBOUNDED_REVOLVING_FEATURES` is
    clipped to the real [winsorize_percentile, 1 - winsorize_percentile]
    quantile range, computed and applied ONLY over applicants WITH real
    revolving-credit history, never over the 0-filled "no history" rows.
    This bounds, never invents, the influence of a small number of
    genuinely extreme real values -- every clipped value is still real,
    just capped to a real, disclosed quantile of the real with-history
    population's own distribution. Returns a third element, a
    `winsorize_report` dict with the exact per-feature bounds and clip
    counts applied -- the calling notebook prints this in full, never
    silently.

    Returns (df, feature_names, winsorize_report) where df has columns
    ["SK_ID_CURR", "HAS_REVOLVING_HISTORY"] + feature_names.
    """
    cc = credit_card.with_columns([
        (pl.col("AMT_BALANCE") / (pl.col("AMT_CREDIT_LIMIT_ACTUAL") + 1.0)).alias("_UTIL"),
        (pl.col("AMT_DRAWINGS_ATM_CURRENT") / (pl.col("AMT_DRAWINGS_CURRENT") + 1.0)).alias("_ATM_SHARE"),
        (pl.col("AMT_DRAWINGS_ATM_CURRENT") > 0).alias("_ANY_CASH_ADVANCE"),
    ])
    cc_min_valid = credit_card.filter(pl.col("AMT_INST_MIN_REGULARITY").is_not_null()).with_columns([
        (pl.col("AMT_PAYMENT_TOTAL_CURRENT") / (pl.col("AMT_INST_MIN_REGULARITY") + 1.0)).alias("_MIN_PAY_RATIO"),
        (pl.col("AMT_PAYMENT_TOTAL_CURRENT") <= pl.col("AMT_INST_MIN_REGULARITY") * 1.05).alias("_MIN_PAY_ONLY"),
    ])

    agg = (
        cc.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("N_CC_MONTHS"),
            pl.col("SK_ID_PREV").n_unique().alias("N_DISTINCT_PREV_CC_LOANS"),
            pl.col("_UTIL").mean().alias("MEAN_UTILIZATION"),
            pl.col("_UTIL").max().alias("MAX_UTILIZATION"),
            (pl.col("_UTIL") > 0.9).mean().alias("PCT_MONTHS_HIGH_UTILIZATION"),
            pl.col("_ATM_SHARE").mean().alias("MEAN_ATM_DRAWINGS_SHARE"),
            pl.col("_ANY_CASH_ADVANCE").mean().alias("PCT_MONTHS_ANY_CASH_ADVANCE"),
            pl.col("SK_DPD").mean().alias("MEAN_SK_DPD"),
            pl.col("SK_DPD").max().alias("MAX_SK_DPD"),
            pl.col("SK_DPD_DEF").mean().alias("MEAN_SK_DPD_DEF"),
            (pl.col("NAME_CONTRACT_STATUS") == "Active").mean().alias("PCT_MONTHS_ACTIVE"),
        ])
        .join(
            cc_min_valid.group_by("SK_ID_CURR").agg([
                pl.col("_MIN_PAY_RATIO").mean().alias("MEAN_MIN_PAYMENT_RATIO"),
                pl.col("_MIN_PAY_ONLY").mean().alias("PCT_MONTHS_MIN_PAYMENT_ONLY"),
            ]),
            on="SK_ID_CURR", how="left",
        )
    )

    feature_names = [c for c in agg.columns if c != "SK_ID_CURR"]
    df = app_ids.select("SK_ID_CURR").join(agg, on="SK_ID_CURR", how="left")
    df = df.with_columns(pl.col("N_CC_MONTHS").is_not_null().alias("HAS_REVOLVING_HISTORY"))
    df = df.with_columns([pl.col(c).fill_null(0.0) for c in feature_names])

    # --- Real winsorization: computed and applied only over applicants WITH
    # real revolving-credit history (see WINSORIZATION DISCLOSURE above).
    winsorize_report: dict = {}
    has_hist_df = df.filter(pl.col("HAS_REVOLVING_HISTORY"))
    for col in UNBOUNDED_REVOLVING_FEATURES:
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
            pl.when(pl.col("HAS_REVOLVING_HISTORY"))
            .then(pl.col(col).clip(lo, hi))
            .otherwise(pl.col(col))
            .alias(col)
        )

    return df, feature_names, winsorize_report
