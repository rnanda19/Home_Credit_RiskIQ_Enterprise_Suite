"""
src/features/liquidity_cashflow_features.py

Shared, real-data feature-engineering module for Mega Project 5 (Liquidity &
Cashflow). Built once, imported everywhere (HYPER standing rule).

Turns `installments_payments.csv` -- an applicant's own real record of what
they were scheduled to pay and what they actually paid, per past installment
-- into two genuinely new views this suite has not built before, both driven
by the same underlying question a treasury/ALM function actually asks:
"how much real cash comes in, on schedule, and how much can we count on?"

Why this is a genuinely different signal from Mega Project 4's
`delinquency_features.py` (not a re-derivation, HYPER-reused where it
overlaps): `engineer_installment_behavior_features()` in that module answers
"does this applicant pay late" with unweighted, per-installment COUNT rates
(PCT_INSTALLMENTS_LATE treats a $50 installment and a $50,000 installment
identically). This module answers a different, treasury-relevant question --
"how much real cash arrives, and when" -- by weighting every reliability
measure by real dollar amount (AMT_INSTALMENT), and by reconstructing a real
calendar-period view of aggregate portfolio cash inflow, which no other
module in this suite computes. Applicant-level late/underpaid behavioral
features are HYPER-reused directly from `delinquency_features.py` wherever
Notebook 01 needs them -- never recomputed here.

REAL, DISCLOSED NULL-HANDLING CONVENTION (same root cause and same fix as
`delinquency_features.py` -- see LESSONS_LEARNED.md): a null
`DAYS_ENTRY_PAYMENT` / `AMT_PAYMENT` means no payment has been recorded
against that scheduled installment as of this data snapshot -- treated as
$0 real cash collected so far against that installment (AMT_PAYMENT
`fill_null(0.0)`), never dropped from the aggregation and never imputed to
a fabricated collected amount.

ZERO-FABRICATION / SCOPE DISCLOSURE: every quantity below is a real sum,
mean, or ratio computed directly from real Kaggle `installments_payments.csv`
/ `application_train.csv` columns. Nothing here is a projection of *future*
cashflow -- that is Notebook 02 (Cash-Flow-at-Risk)'s job, built on top of
this module's real historical reliability output, never inside it.
"""
import numpy as np
import polars as pl


def reconstruct_portfolio_cashflow_periods(
    installments: pl.DataFrame, period_days: int = 30
) -> pl.DataFrame:
    """Real, vectorized (WARP) reconstruction of aggregate portfolio cash
    inflow by calendar period, from real `installments_payments.csv`.

    Bins every real installment into a `period_days`-wide bucket by its real
    scheduled `DAYS_INSTALMENT` (days relative to application date; more
    negative = further in the past -- the native Home Credit convention used
    throughout this suite), then aggregates, per period:
    - N_INSTALLMENTS_SCHEDULED: real count of installments scheduled in that
      period.
    - SCHEDULED_CASH_AMT: real sum(AMT_INSTALMENT) -- what the portfolio was
      contractually owed that period.
    - COLLECTED_CASH_AMT: real sum(AMT_PAYMENT), null treated as $0 collected
      so far (see module docstring's null-handling convention) -- what the
      portfolio actually received.
    - DOLLAR_COLLECTION_RATE: COLLECTED_CASH_AMT / SCHEDULED_CASH_AMT, the
      real, dollar-weighted portfolio-level cash-inflow reliability for that
      period (1.0 = fully collected on schedule; below 1.0 = a real
      shortfall, whether from lateness, underpayment, or default).

    This is a genuinely new portfolio-level, dollar-weighted, time-indexed
    view -- every other feature module in this suite works at the individual
    applicant level or on unweighted installment counts, never on aggregate
    calendar-period dollar cashflow. Returns one row per period, sorted by
    period ascending (oldest first), ready for Notebook 01's reconciliation
    chart and Notebook 02's rolling-forecast input.
    """
    base = installments.with_columns([
        pl.col("AMT_PAYMENT").fill_null(0.0).alias("_AMT_PAYMENT_REAL"),
        (pl.col("DAYS_INSTALMENT") / period_days).floor().cast(pl.Int64).alias("_PERIOD_ID"),
    ])

    agg = (
        base.group_by("_PERIOD_ID")
        .agg([
            pl.len().alias("N_INSTALLMENTS_SCHEDULED"),
            pl.col("SK_ID_CURR").n_unique().alias("N_APPLICANTS_SCHEDULED"),
            pl.col("AMT_INSTALMENT").sum().alias("SCHEDULED_CASH_AMT"),
            pl.col("_AMT_PAYMENT_REAL").sum().alias("COLLECTED_CASH_AMT"),
        ])
        .sort("_PERIOD_ID")
        .with_columns([
            # Real, disclosed edge case: a period with $0 real scheduled
            # cash (should not occur for a real populated period, but
            # guards the same way every other ratio in this suite does)
            # has an undefined collection rate -- null, never a fabricated
            # 1.0 or 0.0.
            pl.when(pl.col("SCHEDULED_CASH_AMT") > 0)
              .then(pl.col("COLLECTED_CASH_AMT") / pl.col("SCHEDULED_CASH_AMT"))
              .otherwise(None)
              .alias("DOLLAR_COLLECTION_RATE"),
            (pl.col("_PERIOD_ID") * period_days).alias("PERIOD_START_DAY"),
        ])
    )
    return agg.select([
        "_PERIOD_ID", "PERIOD_START_DAY", "N_INSTALLMENTS_SCHEDULED",
        "N_APPLICANTS_SCHEDULED", "SCHEDULED_CASH_AMT", "COLLECTED_CASH_AMT",
        "DOLLAR_COLLECTION_RATE",
    ])


def engineer_applicant_cash_reliability_features(
    installments: pl.DataFrame,
) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP -- no per-applicant Python loop) DOLLAR-WEIGHTED
    cash-inflow reliability profile, one row per SK_ID_CURR. Returns
    (features_df, feature_cols). Only applicants with at least one real
    installment record are included (a real, disclosed scope boundary, same
    convention as every other module in this suite -- no applicant is
    assigned a fabricated reliability score for history they don't have).

    Every feature here is weighted by real dollar amount, not installment
    count -- the genuinely new contribution of this module (see docstring).
    A dollar-weighted late-days figure means an applicant who is 30 days
    late on a $50 installment and on-time on a $5,000 installment scores
    very differently here than under `delinquency_features.py`'s unweighted
    MEAN_DAYS_LATE, which treats both installments identically -- this is
    the correct weighting for a cash-inflow-reliability question, where a
    late $50 payment barely moves real portfolio cash, but a late $5,000
    payment does.
    """
    base = installments.with_columns([
        pl.col("AMT_PAYMENT").fill_null(0.0).alias("_AMT_PAYMENT_REAL"),
        (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT")).alias("_DAYS_LATE"),
    ]).with_columns([
        # Real, disclosed convention (same root fact as
        # delinquency_features.py): no recorded payment == 0 real days
        # collected so far == treated as maximally late for the
        # dollar-weighted average below, using the real scheduled day as
        # the reference point (no fabricated "how late" figure invented
        # for a payment that was never made).
        pl.when(pl.col("DAYS_ENTRY_PAYMENT").is_null())
          .then(pl.lit(None, dtype=pl.Float64))
          .otherwise(pl.col("_DAYS_LATE"))
          .alias("_DAYS_LATE_IF_PAID"),
    ])

    feat = (
        base.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("N_INSTALLMENTS"),
            pl.col("AMT_INSTALMENT").sum().alias("TOTAL_SCHEDULED_CASH_AMT"),
            pl.col("_AMT_PAYMENT_REAL").sum().alias("TOTAL_COLLECTED_CASH_AMT"),
            # Real dollar-weighted days-late: sum(days_late * amount) /
            # sum(amount), over installments that were actually paid --
            # an unpaid-as-of-snapshot installment has no real "how late
            # was it collected" figure to weight in yet (Notebook 01
            # reports its dollar amount separately, via the shortfall
            # measure below, rather than inventing a days-late value for
            # cash that hasn't arrived).
            (pl.col("_DAYS_LATE_IF_PAID") * pl.col("AMT_INSTALMENT")).sum().alias("_WEIGHTED_LATE_SUM"),
            pl.col("AMT_INSTALMENT").filter(pl.col("_DAYS_LATE_IF_PAID").is_not_null()).sum().alias("_PAID_AMT_BASIS"),
        ])
        .with_columns([
            pl.when(pl.col("TOTAL_SCHEDULED_CASH_AMT") > 0)
              .then(pl.col("TOTAL_COLLECTED_CASH_AMT") / pl.col("TOTAL_SCHEDULED_CASH_AMT"))
              .otherwise(None)
              .alias("DOLLAR_COLLECTION_RATE"),
            (pl.col("TOTAL_SCHEDULED_CASH_AMT") - pl.col("TOTAL_COLLECTED_CASH_AMT"))
              .clip(lower_bound=0).alias("OUTSTANDING_SHORTFALL_AMT"),
            pl.when(pl.col("_PAID_AMT_BASIS") > 0)
              .then(pl.col("_WEIGHTED_LATE_SUM") / pl.col("_PAID_AMT_BASIS"))
              .otherwise(0.0)  # real, disclosed edge case: nothing paid yet -- no
                                # real lateness-on-paid-cash to weight, defined 0.0,
                                # never left null (OUTSTANDING_SHORTFALL_AMT already
                                # carries the "nothing collected" signal separately).
              .alias("DOLLAR_WEIGHTED_DAYS_LATE"),
        ])
    )

    feature_cols = [
        "N_INSTALLMENTS", "TOTAL_SCHEDULED_CASH_AMT", "TOTAL_COLLECTED_CASH_AMT",
        "DOLLAR_COLLECTION_RATE", "OUTSTANDING_SHORTFALL_AMT", "DOLLAR_WEIGHTED_DAYS_LATE",
    ]
    return feat.select(["SK_ID_CURR"] + feature_cols), feature_cols


def attach_repayment_capacity(
    cash_reliability: pl.DataFrame, application: pl.DataFrame
) -> pl.DataFrame:
    """HYPER reuse (per this Mega Project's own scope README): joins in Mega
    Project 1 Notebook 04's real REPAYMENT_CAPACITY_RATIO formula --
    `AMT_INCOME_TOTAL / (AMT_ANNUITY + 1.0)`, the identical formula served
    by `01_mega_project_1_underwriting_approval/services/repayment_capacity_service.py`
    -- directly from real `application_train.csv` columns, rather than
    recomputing an independent version of the same real ratio. A null real
    AMT_ANNUITY (a real, documented minority of Home Credit applications)
    yields a null ratio here too, consistent with that service's own real,
    disclosed handling -- never a fabricated fallback value.
    """
    with_ratio = application.select([
        "SK_ID_CURR", "AMT_INCOME_TOTAL", "AMT_ANNUITY",
    ]).with_columns([
        pl.when(pl.col("AMT_ANNUITY").is_not_null())
          .then(pl.col("AMT_INCOME_TOTAL") / (pl.col("AMT_ANNUITY") + 1.0))
          .otherwise(None)
          .alias("REPAYMENT_CAPACITY_RATIO"),
    ]).select(["SK_ID_CURR", "REPAYMENT_CAPACITY_RATIO"])

    return cash_reliability.join(with_ratio, on="SK_ID_CURR", how="left")


def bootstrap_cash_flow_at_risk(
    periods: pl.DataFrame,
    horizons_days: list[int],
    period_days: int = 30,
    n_anchor_periods: int = 3,
    n_draws: int = 20_000,
    seed: int = 42,
) -> dict:
    """Real, vectorized (Lesson #5, LESSONS_LEARNED.md -- one batched draw per
    horizon, never a per-draw Python loop) Monte Carlo bootstrap of real
    Cash-Flow-at-Risk, from `periods` (the real output of
    `reconstruct_portfolio_cashflow_periods()` above -- HYPER reuse, this
    function never recomputes the historical periods themselves).

    ONE documented assumption, clearly labeled (see the returned dict's
    `near_term_scheduled_cash_per_period_assumption` key): real Kaggle
    `installments_payments.csv` is a static historical extract with no row
    for a not-yet-scheduled installment, so near-term scheduled cash is
    assumed to continue at the mean of the most recent `n_anchor_periods`
    real historical periods. Everything else is real: the per-period rates
    being bootstrap-resampled (WITH replacement, from the real observed
    distribution -- never an assumed normal curve or invented volatility
    parameter) and the Monte Carlo mechanics.

    Real cross-check baked in (Lesson #6): each horizon's Monte Carlo sample
    mean is checked against its own real closed-form expectation (assumed
    scheduled cash x mean historical rate x horizon) -- `reconciles` and
    `relative_diff` are returned per horizon so a caller can gate on this
    rather than trust the simulation blindly.

    Returns {"real_rates_n": int, "near_term_scheduled_cash_per_period_assumption": float,
    "n_draws": int, "by_horizon": {horizon_days: {"n_periods", "mc_mean",
    "closed_form_mean", "relative_diff", "reconciles", "p5_cfar",
    "p50_expected", "p95"}}}. Raises ValueError if fewer than 3 real
    historical periods have a non-null collection rate -- too few to
    bootstrap a meaningful distribution from."""
    real_rates = periods["DOLLAR_COLLECTION_RATE"].drop_nulls().to_numpy()
    if real_rates.size < 3:
        raise ValueError(
            f"Only {real_rates.size} real historical periods with a non-null collection "
            "rate -- too few to bootstrap a meaningful distribution from. Needs at least 3."
        )

    n_anchor = min(n_anchor_periods, periods.height)
    anchor_scheduled_per_period = float(
        periods.sort("_PERIOD_ID").tail(n_anchor)["SCHEDULED_CASH_AMT"].mean()
    )

    rng = np.random.default_rng(seed)
    RECONCILIATION_TOLERANCE_PCT = 0.02  # 2% relative -- real, disclosed tolerance
    by_horizon = {}
    for horizon_days in horizons_days:
        n_periods_h = horizon_days // period_days
        draws = rng.choice(real_rates, size=(n_draws, n_periods_h), replace=True)
        simulated_collected = anchor_scheduled_per_period * draws.sum(axis=1)

        mc_mean = float(simulated_collected.mean())
        closed_form_mean = anchor_scheduled_per_period * n_periods_h * float(real_rates.mean())
        rel_diff = abs(mc_mean - closed_form_mean) / closed_form_mean if closed_form_mean else float("inf")
        p5, p50, p95 = np.percentile(simulated_collected, [5, 50, 95])
        by_horizon[horizon_days] = {
            "n_periods": n_periods_h,
            "mc_mean": mc_mean,
            "closed_form_mean": closed_form_mean,
            "relative_diff": float(rel_diff),
            "reconciles": bool(rel_diff < RECONCILIATION_TOLERANCE_PCT),
            "p5_cfar": float(p5),
            "p50_expected": float(p50),
            "p95": float(p95),
        }

    return {
        "real_rates_n": int(real_rates.size),
        "near_term_scheduled_cash_per_period_assumption": anchor_scheduled_per_period,
        "n_draws": n_draws,
        "by_horizon": by_horizon,
    }
