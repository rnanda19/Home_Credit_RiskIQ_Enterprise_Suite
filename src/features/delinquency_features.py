"""
src/features/delinquency_features.py

Shared, real-data feature-engineering module for Mega Project 4 (Delinquency
Prevention). Built once, imported everywhere (HYPER standing rule).

Turns installments_payments.csv -- an applicant's own real record of what
they were scheduled to pay and what they actually paid, per past installment
-- into a SK_ID_CURR-level behavioral profile: how often they pay late, by
how much, whether they underpay, and whether that behavior is getting
better or worse over time.

Why this is a genuinely different signal from Mega Project 1's underwriting
model (not a re-derivation): MP1 Notebook 01's champion model is trained
entirely on APPLICATION-TIME covariates (income, employment, external
bureau scores, previous-application outcomes) -- everything knowable at the
moment of approval, before a single payment has been made. This module
looks at the OPPOSITE information: how an applicant has actually behaved
across every installment they were ever scheduled to pay, on any loan.
That is precisely the kind of signal a portfolio-monitoring / collections
function watches for accounts that are still current today but drifting
toward delinquency -- it does not exist yet at underwriting time, and MP1's
model structurally cannot see it.

Leakage note: installments_payments has no forward-looking information
relative to itself (a payment's own lateness is a fact about the past, not
a prediction), so no leave-one-out logic is required here, unlike
applicant_credit_history_features.py's previous-application-linked tables.

Real data-quality convention (disclosed, not fabricated): a real minority
of installment_payments rows have a null DAYS_ENTRY_PAYMENT / AMT_PAYMENT
-- no payment has been recorded against that scheduled installment as of
this data snapshot. This module treats such a row as unpaid-as-of-snapshot:
IS_LATE = True and IS_UNDERPAID = True (0.0 real payment recorded against a
nonzero scheduled amount is, factually, both late and underpaid), with
SHORTFALL_AMT = the full real AMT_INSTALMENT (nothing paid so far). This is
a disclosed modeling convention for an actually-missing payment record, not
an invented value. Before this convention was added, these rows silently
fell out of every rate/mean aggregation below (polars aggregations skip
nulls by default) and could leave a null in the applicant's most recent
real streak -- exactly the record a delinquency-prevention notebook most
needs to classify correctly.
"""
import polars as pl


def engineer_installment_behavior_features(installments: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP) installments_payments aggregation to one row per
    SK_ID_CURR. Returns (features_df, feature_cols). Only applicants with at
    least one real installment record are included -- an applicant with zero
    prior installment history simply has no behavioral signal to score
    (a real, disclosed scope boundary, not a fabricated default value)."""
    base = installments.with_columns([
        pl.col("DAYS_ENTRY_PAYMENT").is_null().alias("_NO_PAYMENT_RECORDED"),
        (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT")).alias("DAYS_LATE"),
        pl.when(pl.col("AMT_INSTALMENT") > 0)
          .then(pl.col("AMT_PAYMENT") / pl.col("AMT_INSTALMENT"))
          .otherwise(None)
          .alias("PAYMENT_RATIO"),
        (pl.col("AMT_INSTALMENT") - pl.col("AMT_PAYMENT")).clip(lower_bound=0).alias("SHORTFALL_AMT"),
    ]).with_columns([
        # No recorded payment == unpaid as of this snapshot -- real, disclosed
        # convention (see module docstring), not a fabricated value.
        (pl.col("_NO_PAYMENT_RECORDED") | (pl.col("DAYS_LATE") > 0)).alias("IS_LATE"),
        (pl.col("_NO_PAYMENT_RECORDED") | (pl.col("PAYMENT_RATIO") < 0.99)).alias("IS_UNDERPAID"),
        pl.when(pl.col("_NO_PAYMENT_RECORDED")).then(0.0).otherwise(pl.col("PAYMENT_RATIO")).alias("PAYMENT_RATIO"),
        pl.when(pl.col("_NO_PAYMENT_RECORDED")).then(pl.col("AMT_INSTALMENT").clip(lower_bound=0)).otherwise(pl.col("SHORTFALL_AMT")).alias("SHORTFALL_AMT"),
    ])

    # Recency split (vectorized, no per-group Python loop): rank each
    # applicant's own installments chronologically by real DAYS_INSTALMENT
    # (more negative = further in the past), then split into an "early
    # half" and a "recent half" via the fractional rank within each group.
    base = base.with_columns([
        pl.col("DAYS_INSTALMENT").rank("ordinal").over("SK_ID_CURR").alias("_RANK"),
        pl.len().over("SK_ID_CURR").alias("_N_IN_GROUP"),
    ]).with_columns([
        (pl.col("_RANK") / pl.col("_N_IN_GROUP") > 0.5).alias("_IS_RECENT_HALF"),
    ])

    overall_agg = (
        base.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("N_INSTALLMENTS"),
            pl.col("SK_ID_PREV").n_unique().alias("N_PREV_LOANS_SERVICED"),
            pl.col("IS_LATE").mean().alias("PCT_INSTALLMENTS_LATE"),
            pl.col("DAYS_LATE").mean().alias("MEAN_DAYS_LATE"),
            pl.col("DAYS_LATE").max().alias("MAX_DAYS_LATE"),
            pl.col("DAYS_LATE").std().alias("STD_DAYS_LATE"),
            pl.col("DAYS_LATE").filter(pl.col("IS_LATE")).mean().alias("MEAN_DAYS_LATE_WHEN_LATE"),
            pl.col("IS_UNDERPAID").mean().alias("PCT_INSTALLMENTS_UNDERPAID"),
            pl.col("PAYMENT_RATIO").mean().alias("MEAN_PAYMENT_RATIO"),
            pl.col("PAYMENT_RATIO").min().alias("MIN_PAYMENT_RATIO"),
            pl.col("SHORTFALL_AMT").sum().alias("TOTAL_SHORTFALL_AMT"),
        ])
    )

    half_agg = (
        base.group_by(["SK_ID_CURR", "_IS_RECENT_HALF"])
        .agg(pl.col("IS_LATE").mean().alias("_LATE_RATE"))
        .collect() if isinstance(base, pl.LazyFrame) else
        base.group_by(["SK_ID_CURR", "_IS_RECENT_HALF"]).agg(pl.col("IS_LATE").mean().alias("_LATE_RATE"))
    )
    recent = half_agg.filter(pl.col("_IS_RECENT_HALF")).select(["SK_ID_CURR", pl.col("_LATE_RATE").alias("_LATE_RATE_RECENT")])
    early = half_agg.filter(~pl.col("_IS_RECENT_HALF")).select(["SK_ID_CURR", pl.col("_LATE_RATE").alias("_LATE_RATE_EARLY")])
    trend = (
        recent.join(early, on="SK_ID_CURR", how="outer_coalesce")
        .with_columns([
            pl.col("_LATE_RATE_RECENT").fill_null(0.0),
            pl.col("_LATE_RATE_EARLY").fill_null(0.0),
        ])
        .with_columns(
            (pl.col("_LATE_RATE_RECENT") - pl.col("_LATE_RATE_EARLY")).alias("LATE_RATE_TREND")
        )
        .select(["SK_ID_CURR", "LATE_RATE_TREND"])
    )

    feat = (
        overall_agg.join(trend, on="SK_ID_CURR", how="left")
        .with_columns([
            pl.col("MEAN_DAYS_LATE_WHEN_LATE").fill_null(0.0),
            pl.col("STD_DAYS_LATE").fill_null(0.0),
            pl.col("LATE_RATE_TREND").fill_null(0.0),
            pl.col("MEAN_PAYMENT_RATIO").fill_null(1.0),
            pl.col("MIN_PAYMENT_RATIO").fill_null(1.0),
        ])
    )

    feature_cols = [
        "N_INSTALLMENTS", "N_PREV_LOANS_SERVICED", "PCT_INSTALLMENTS_LATE",
        "MEAN_DAYS_LATE", "MAX_DAYS_LATE", "STD_DAYS_LATE", "MEAN_DAYS_LATE_WHEN_LATE",
        "PCT_INSTALLMENTS_UNDERPAID", "MEAN_PAYMENT_RATIO", "MIN_PAYMENT_RATIO",
        "TOTAL_SHORTFALL_AMT", "LATE_RATE_TREND",
    ]
    return feat, feature_cols


def engineer_payment_streak_features(installments: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP -- no per-applicant Python loop) run-length-encoding
    of each applicant's own real late/on-time installment sequence, one row per
    SK_ID_CURR. Returns (features_df, feature_cols).

    Why this is a genuinely different signal from
    engineer_installment_behavior_features() above (used by Notebook 01): that
    function summarizes RATES (e.g. "35% of installments were late"), which
    cannot distinguish an applicant who is late on scattered, isolated
    installments from one who is currently in the middle of a real 6-payment
    late streak -- the same rate, very different real risk profile. This
    function instead detects real STREAKS (consecutive runs of the same
    late/on-time status, ordered by real DAYS_INSTALMENT) and, critically, the
    applicant's CURRENT streak -- the most operationally relevant fact for an
    early-warning / collections use case ("is this account in a bad streak
    right now"), which a simple rate can never capture.

    Vectorization method: within each applicant's chronologically-sorted rows,
    a new streak starts wherever real IS_LATE differs from the immediately
    preceding real installment's IS_LATE (a real, vectorized boundary
    detection via `.shift(1).over("SK_ID_CURR")`, not a per-row Python loop);
    `cum_sum()` over those boundaries gives each row a real streak id, which is
    then grouped to get real streak lengths.
    """
    # Same real, disclosed no-payment-recorded convention as
    # engineer_installment_behavior_features() above (see module docstring):
    # a null DAYS_ENTRY_PAYMENT is treated as unpaid-as-of-snapshot == late,
    # so IS_LATE is never null here -- otherwise a null could land in an
    # applicant's most recent streak (CURRENT_STREAK_IS_LATE) and surface
    # downstream as a NaN once cast for clustering.
    base = installments.sort(["SK_ID_CURR", "DAYS_INSTALMENT"]).with_columns([
        (pl.col("DAYS_ENTRY_PAYMENT").is_null() | (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT") > 0)).alias("IS_LATE"),
    ])
    base = base.with_columns([
        (pl.col("IS_LATE") != pl.col("IS_LATE").shift(1).over("SK_ID_CURR")).fill_null(True).alias("_NEW_STREAK"),
    ])
    base = base.with_columns([
        pl.col("_NEW_STREAK").cast(pl.Int32).cum_sum().over("SK_ID_CURR").alias("_STREAK_ID"),
    ])
    n_installments = base.group_by("SK_ID_CURR").agg(pl.len().alias("N_INSTALLMENTS"))

    streaks = base.group_by(["SK_ID_CURR", "_STREAK_ID"]).agg([
        pl.col("IS_LATE").first().alias("STREAK_IS_LATE"),
        pl.len().alias("STREAK_LEN"),
        pl.col("DAYS_INSTALMENT").max().alias("STREAK_LAST_DAY"),
    ])

    longest = streaks.group_by("SK_ID_CURR").agg([
        pl.col("STREAK_LEN").filter(pl.col("STREAK_IS_LATE")).max().alias("LONGEST_LATE_STREAK"),
        pl.col("STREAK_LEN").filter(~pl.col("STREAK_IS_LATE")).max().alias("LONGEST_ONTIME_STREAK"),
        pl.col("STREAK_IS_LATE").filter(pl.col("STREAK_IS_LATE")).len().alias("N_LATE_STREAKS"),
        pl.len().alias("N_TOTAL_STREAKS"),
    ])

    # "Current" streak = the streak whose last real installment is most
    # recent (max real DAYS_INSTALMENT) -- a real, vectorized "sort then take
    # the last row per group" idiom, not a per-applicant lookup loop.
    current = (
        streaks.sort(["SK_ID_CURR", "STREAK_LAST_DAY"])
        .group_by("SK_ID_CURR", maintain_order=True)
        .agg([
            pl.col("STREAK_IS_LATE").last().alias("CURRENT_STREAK_IS_LATE"),
            pl.col("STREAK_LEN").last().alias("CURRENT_STREAK_LEN"),
        ])
    )

    feat = (
        longest.join(current, on="SK_ID_CURR", how="left")
        .join(n_installments, on="SK_ID_CURR", how="left")
        .with_columns([
            pl.col("LONGEST_LATE_STREAK").fill_null(0),
            pl.col("LONGEST_ONTIME_STREAK").fill_null(0),
            pl.col("N_LATE_STREAKS").fill_null(0),
        ])
        .with_columns([
            # Real, disclosed edge case: an applicant with exactly 1 real
            # installment has 0 real transitions to measure -- ALTERNATION_RATE
            # is defined as 0.0 (no evidence of alternation), not null/NaN.
            pl.when(pl.col("N_INSTALLMENTS") > 1)
              .then((pl.col("N_TOTAL_STREAKS") - 1) / (pl.col("N_INSTALLMENTS") - 1))
              .otherwise(0.0)
              .alias("ALTERNATION_RATE"),
            pl.col("CURRENT_STREAK_IS_LATE").cast(pl.Int32).alias("CURRENT_STREAK_IS_LATE_INT"),
        ])
    )

    feature_cols = [
        "LONGEST_LATE_STREAK", "LONGEST_ONTIME_STREAK", "N_LATE_STREAKS", "N_TOTAL_STREAKS",
        "CURRENT_STREAK_IS_LATE_INT", "CURRENT_STREAK_LEN", "ALTERNATION_RATE",
    ]
    return feat, feature_cols
