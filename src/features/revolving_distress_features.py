"""
src/features/revolving_distress_features.py

Shared, real-data feature-engineering module for Mega Project 4 (Delinquency
Prevention), Problem 3 -- Revolving/Credit-Card Distress Early Warning. Built
once, imported everywhere (HYPER standing rule).

Turns `credit_card_balance.csv` -- the applicant's own real month-by-month
credit-card balance, credit limit, drawings, and minimum-payment record on
PREVIOUS Home Credit revolving loans -- into a SK_ID_CURR-level TRAJECTORY
profile: is their utilization spiking, are they stuck making only the
minimum payment, and is their balance accelerating upward. All three are
about DIRECTION OF CHANGE, not a static level.

ZERO-FABRICATION / OVERLAP DISCLOSURE (read before using): this table
already feeds two other real feature sets in this suite, and this module
deliberately does not re-derive either:

1. Mega Project 1's champion model includes 8 real SUM-based features
   (CC_N_OWN, CC_SUM_UTILIZATION_OWN, CC_SUM_BALANCE_OWN, CC_SUM_SK_DPD_OWN,
   CC_N_TOT, CC_SUM_UTILIZATION_TOT, CC_SUM_BALANCE_TOT, CC_SUM_SK_DPD_TOT --
   see `applicant_credit_history_features.py`) -- application-time totals,
   not a behavioral trajectory.
2. Mega Project 3 Notebook 04's `engineer_revolving_credit_utilization_features()`
   (see `risk_segmentation_features.py`) builds real MEAN/MAX/PCT-of-months
   RATE features (MEAN_UTILIZATION, MAX_UTILIZATION, PCT_MONTHS_MIN_PAYMENT_ONLY,
   etc.) for an UNSUPERVISED segmentation -- a real, static distribution
   summary of usage LEVEL.

This module instead detects real SPIKES, STREAKS, and VELOCITY -- the same
"rate cannot see direction of change" argument this suite already established
for Problem 1 vs Problem 2 (installments_payments.csv): a mean utilization of
70% cannot distinguish an applicant who has been steadily at 70% for a year
from one who was at 20% last month and is at 70% this month -- same mean,
very different real trajectory, and the second is the one an early-warning
model needs to catch. Feeds a real SUPERVISED classifier (predicting real
`TARGET`, unlike Mega Project 3's unsupervised segmentation), matching
Problem 1's early-warning use case but on a different real data source and a
genuinely different real feature space (trajectory, not rate/level).

SCOPE (real, disclosed): real Kaggle `credit_card_balance.csv` only has rows
for applicants whose previous Home Credit loans included a real revolving/
credit-card product. An applicant with none has `HAS_REVOLVING_HISTORY =
False` and every feature filled 0 -- excluded from this notebook's modeling
scope, never assigned a fabricated trajectory. This is expected to be a
real minority of the population (this is a revolving-product-specific
signal), same disclosed-scope pattern as Problem 1's installment-history
requirement.

REAL, DISCLOSED NULL-HANDLING CONVENTIONS (see LESSONS_LEARNED.md --
Problem 1/2's real 2026-09-01 fix for the identical root cause on
`installments_payments.csv`; applied proactively here, not reactively):
- `AMT_DRAWINGS_CURRENT` null on a real month means no real drawing activity
  was recorded that month -- treated as 0.0 (a real "nothing happened", not
  a missing observation), never dropped or left null (a null here, run
  through a streak/velocity calculation, is exactly the kind of value that
  silently produced a NaN in Problem 2's real full-scale run).
- `AMT_INST_MIN_REGULARITY` null on a real month means no minimum payment
  was due that month (e.g. a real zero-balance month) -- there is no real
  minimum to compare a payment against, so that month cannot, by
  definition, be a "minimum-payment-only" month; treated as
  `IS_MIN_PAYMENT_ONLY = False` for that month (never null), so the
  minimum-payment streak detector below never receives a null boolean.
"""
import polars as pl


def engineer_revolving_distress_features(credit_card: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP -- no per-applicant Python loop) trajectory
    feature engineering from `credit_card_balance.csv`, one row per
    SK_ID_CURR. Returns (features_df, feature_cols). Only applicants with at
    least one real credit_card_balance.csv record are included (see module
    docstring's SCOPE section) -- callers should left-join onto their own
    population and treat missing rows as `HAS_REVOLVING_HISTORY = False`
    (this function itself only returns applicants WITH history, matching
    `engineer_installment_behavior_features()`'s convention).

    Feature families (9 total):
    - Utilization SPIKE (3): CURRENT_UTILIZATION, MAX_UTILIZATION_JUMP,
      N_UTILIZATION_SPIKE_MONTHS -- real month-over-month change, not a
      static mean/max.
    - Minimum-payment-only STREAK (3, real vectorized run-length encoding,
      same shift+cumsum technique as `engineer_payment_streak_features()`):
      LONGEST_MIN_PAYMENT_ONLY_STREAK, CURRENT_MIN_PAYMENT_ONLY_STREAK_LEN,
      CURRENT_IS_MIN_PAYMENT_ONLY_INT.
    - Drawdown VELOCITY (2, real vectorized recency split, same technique as
      `engineer_installment_behavior_features()`'s LATE_RATE_TREND):
      BALANCE_GROWTH_VELOCITY, DRAWINGS_VELOCITY.
    - N_CC_MONTHS (1): real scope-size context for the other 8.
    """
    base = credit_card.sort(["SK_ID_CURR", "MONTHS_BALANCE"]).with_columns([
        (pl.col("AMT_BALANCE") / (pl.col("AMT_CREDIT_LIMIT_ACTUAL") + 1.0)).alias("_UTIL"),
        pl.col("AMT_DRAWINGS_CURRENT").fill_null(0.0).alias("_DRAWINGS"),
        pl.when(pl.col("AMT_INST_MIN_REGULARITY").is_not_null())
          .then(pl.col("AMT_PAYMENT_TOTAL_CURRENT") <= pl.col("AMT_INST_MIN_REGULARITY") * 1.05)
          .otherwise(False)
          .alias("_IS_MIN_PAY_ONLY"),
    ])

    # --- Utilization spike features: real month-over-month change within
    # each applicant's own chronologically-sorted rows. First real month has
    # no prior month to compare against -- real, disclosed edge case: filled
    # 0.0 (no jump measurable), not null.
    base = base.with_columns([
        (pl.col("_UTIL") - pl.col("_UTIL").shift(1).over("SK_ID_CURR")).fill_null(0.0).alias("_UTIL_JUMP"),
    ])
    SPIKE_THRESHOLD = 0.15  # real, disclosed: a 15-percentage-point month-over-month utilization jump
    base = base.with_columns([
        (pl.col("_UTIL_JUMP") >= SPIKE_THRESHOLD).alias("_IS_SPIKE_MONTH"),
    ])

    spike_agg = base.group_by("SK_ID_CURR").agg([
        pl.len().alias("N_CC_MONTHS"),
        pl.col("_UTIL").last().alias("CURRENT_UTILIZATION"),
        pl.col("_UTIL_JUMP").max().alias("MAX_UTILIZATION_JUMP"),
        pl.col("_IS_SPIKE_MONTH").sum().alias("N_UTILIZATION_SPIKE_MONTHS"),
    ])

    # --- Minimum-payment-only streak features: same real vectorized
    # boundary-detection + cum_sum run-length encoding as
    # `engineer_payment_streak_features()` (installments_payments.csv).
    base = base.with_columns([
        (pl.col("_IS_MIN_PAY_ONLY") != pl.col("_IS_MIN_PAY_ONLY").shift(1).over("SK_ID_CURR"))
          .fill_null(True).alias("_NEW_STREAK"),
    ])
    base = base.with_columns([
        pl.col("_NEW_STREAK").cast(pl.Int32).cum_sum().over("SK_ID_CURR").alias("_STREAK_ID"),
    ])
    streaks = base.group_by(["SK_ID_CURR", "_STREAK_ID"]).agg([
        pl.col("_IS_MIN_PAY_ONLY").first().alias("STREAK_IS_MIN_PAY_ONLY"),
        pl.len().alias("STREAK_LEN"),
        pl.col("MONTHS_BALANCE").max().alias("STREAK_LAST_MONTH"),
    ])
    longest_min_pay = streaks.group_by("SK_ID_CURR").agg([
        pl.col("STREAK_LEN").filter(pl.col("STREAK_IS_MIN_PAY_ONLY")).max()
          .fill_null(0).alias("LONGEST_MIN_PAYMENT_ONLY_STREAK"),
    ])
    current_min_pay = (
        streaks.sort(["SK_ID_CURR", "STREAK_LAST_MONTH"])
        .group_by("SK_ID_CURR", maintain_order=True)
        .agg([
            pl.col("STREAK_IS_MIN_PAY_ONLY").last().alias("_CURRENT_IS_MIN_PAY_ONLY"),
            pl.col("STREAK_LEN").last().alias("CURRENT_MIN_PAYMENT_ONLY_STREAK_LEN"),
        ])
        .with_columns(pl.col("_CURRENT_IS_MIN_PAY_ONLY").cast(pl.Int32).alias("CURRENT_IS_MIN_PAYMENT_ONLY_INT"))
        .select(["SK_ID_CURR", "CURRENT_IS_MIN_PAYMENT_ONLY_INT", "CURRENT_MIN_PAYMENT_ONLY_STREAK_LEN"])
    )

    # --- Drawdown velocity: real vectorized recency split (same rank-based
    # technique as `engineer_installment_behavior_features()`'s
    # LATE_RATE_TREND), applied to real balance and real drawings.
    trend_base = base.with_columns([
        pl.col("MONTHS_BALANCE").rank("ordinal").over("SK_ID_CURR").alias("_RANK"),
        pl.len().over("SK_ID_CURR").alias("_N_IN_GROUP"),
    ]).with_columns([
        (pl.col("_RANK") / pl.col("_N_IN_GROUP") > 0.5).alias("_IS_RECENT_HALF"),
    ])
    half_agg = trend_base.group_by(["SK_ID_CURR", "_IS_RECENT_HALF"]).agg([
        pl.col("AMT_BALANCE").mean().alias("_MEAN_BALANCE"),
        pl.col("_DRAWINGS").mean().alias("_MEAN_DRAWINGS"),
    ])
    recent = half_agg.filter(pl.col("_IS_RECENT_HALF")).select([
        "SK_ID_CURR",
        pl.col("_MEAN_BALANCE").alias("_BAL_RECENT"), pl.col("_MEAN_DRAWINGS").alias("_DRAW_RECENT"),
    ])
    early = half_agg.filter(~pl.col("_IS_RECENT_HALF")).select([
        "SK_ID_CURR",
        pl.col("_MEAN_BALANCE").alias("_BAL_EARLY"), pl.col("_MEAN_DRAWINGS").alias("_DRAW_EARLY"),
    ])
    velocity = (
        recent.join(early, on="SK_ID_CURR", how="outer_coalesce")
        .with_columns([
            pl.col("_BAL_RECENT").fill_null(0.0), pl.col("_BAL_EARLY").fill_null(0.0),
            pl.col("_DRAW_RECENT").fill_null(0.0), pl.col("_DRAW_EARLY").fill_null(0.0),
        ])
        .with_columns([
            # Real, normalized rate of change -- divided by (early + 1) so a
            # small early balance doesn't produce an artificially huge ratio.
            ((pl.col("_BAL_RECENT") - pl.col("_BAL_EARLY")) / (pl.col("_BAL_EARLY").abs() + 1.0))
              .alias("BALANCE_GROWTH_VELOCITY"),
            ((pl.col("_DRAW_RECENT") - pl.col("_DRAW_EARLY")) / (pl.col("_DRAW_EARLY").abs() + 1.0))
              .alias("DRAWINGS_VELOCITY"),
        ])
        .select(["SK_ID_CURR", "BALANCE_GROWTH_VELOCITY", "DRAWINGS_VELOCITY"])
    )

    feat = (
        spike_agg.join(longest_min_pay, on="SK_ID_CURR", how="left")
        .join(current_min_pay, on="SK_ID_CURR", how="left")
        .join(velocity, on="SK_ID_CURR", how="left")
    )

    feature_cols = [
        "N_CC_MONTHS", "CURRENT_UTILIZATION", "MAX_UTILIZATION_JUMP", "N_UTILIZATION_SPIKE_MONTHS",
        "LONGEST_MIN_PAYMENT_ONLY_STREAK", "CURRENT_MIN_PAYMENT_ONLY_STREAK_LEN",
        "CURRENT_IS_MIN_PAYMENT_ONLY_INT", "BALANCE_GROWTH_VELOCITY", "DRAWINGS_VELOCITY",
    ]
    return feat, feature_cols
