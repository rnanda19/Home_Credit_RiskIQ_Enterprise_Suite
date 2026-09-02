"""
src/features/pos_cash_trajectory_features.py

Shared, real-data feature-engineering module for Mega Project 4 (Delinquency
Prevention), Problem 4 -- POS/Cash Loan Delinquency Trajectory. Built once,
imported everywhere (HYPER standing rule).

Turns `POS_CASH_balance.csv` -- the applicant's own real month-by-month
days-past-due (DPD) tracking and remaining-instalment count on PREVIOUS
Home Credit point-of-sale / cash (non-revolving instalment) loans -- into a
SK_ID_CURR-level TRAJECTORY profile: is real DPD spiking or streaking, and
is real repayment progress stalling, rather than a static level.

ZERO-FABRICATION / OVERLAP DISCLOSURE (read before using): this table
already feeds two other real feature sets in this suite:

1. Mega Project 1's champion model includes real SUM totals
   (`POS_SUM_SK_DPD_OWN`, `POS_SUM_SK_DPD_DEF_OWN`, `POS_SUM_SK_DPD_TOT`,
   `POS_SUM_SK_DPD_DEF_TOT` -- see `applicant_credit_history_features.py`)
   -- application-time totals, not a trajectory.
2. Mega Project 3 Notebook 03's `engineer_repayment_behavior_features()`
   (see `risk_segmentation_features.py`) builds real MEAN/MAX/PCT-of-months
   RATE/LEVEL features (`MEAN_SK_DPD`, `MAX_SK_DPD`, `MEAN_SK_DPD_DEF`,
   `PCT_MONTHS_ACTIVE`, `PCT_MONTHS_COMPLETED`) for an UNSUPERVISED
   segmentation -- a real, static distribution summary.

This module instead detects real DPD SPIKES and STREAKS, and real
repayment-PROGRESS STALLING -- the same "a level/rate cannot see direction
of change" argument this suite has now established three times (Problem 1
vs 2, and Problem 3 vs MP1/MP3 Notebook 04). A mean DPD of 3 days cannot
distinguish an applicant who has had a scattered 3-day slip once from one
who is CURRENTLY in the middle of a real DPD streak -- same mean, very
different real trajectory. Feeds a real SUPERVISED classifier (predicting
real `TARGET`), matching Problems 1 and 3's early-warning use case but on a
third real data source and a genuinely different real feature space.

SCOPE (real, disclosed): real Kaggle `POS_CASH_balance.csv` only has rows
for applicants whose previous Home Credit loans included a real POS/cash
(non-revolving instalment) product. An applicant with none has
`HAS_POS_CASH_HISTORY = False` and every feature filled 0 -- excluded from
this notebook's modeling scope, never assigned a fabricated trajectory.

REAL, DISCLOSED NULL-HANDLING CONVENTIONS (proactively applied -- see
LESSONS_LEARNED.md, Problems 1-2's real 2026-09-01 fix for the identical
root cause on a different real table):
- `SK_DPD` is defensively `fill_null(0)` before use (real Home Credit data
  always populates it with 0 when no real delinquency exists, but this
  guards the boundary-detection streak logic below against ever receiving
  a null boolean, the exact root cause of Problem 2's real crash).
- `CNT_INSTALMENT_FUTURE` (real remaining-instalment count) has a real,
  documented minority of null rows in the actual Kaggle file. Rather than
  filling a fabricated remaining-count, null rows are dropped from the
  progress-velocity MEAN aggregation only (an established, already-used
  suite convention -- `.mean()` over real non-null values, same as
  Problem 1's `MEAN_DAYS_LATE`) -- but the final aggregated
  `INSTALMENT_PROGRESS_VELOCITY` value is `fill_null(0.0)` at the very end
  (an applicant whose real months all happen to be null in this column has
  no real progress signal, treated as neutral 0.0, never left as a null
  that could reach the classifier as NaN).
"""
import polars as pl


def engineer_pos_cash_trajectory_features(pos_cash: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP -- no per-applicant Python loop) trajectory
    feature engineering from `POS_CASH_balance.csv`, one row per SK_ID_CURR.
    Returns (features_df, feature_cols). Only applicants with at least one
    real POS_CASH_balance.csv record are included (see module docstring's
    SCOPE section) -- callers should left-join onto their own population and
    treat missing rows as `HAS_POS_CASH_HISTORY = False`.

    Feature families (8 total):
    - DPD SPIKE/STREAK (5, real vectorized run-length encoding, same
      shift+cumsum technique as `engineer_payment_streak_features()` and
      `engineer_revolving_distress_features()`'s min-payment-only streak):
      CURRENT_SK_DPD, MAX_DPD_JUMP, N_DPD_SPIKE_MONTHS,
      LONGEST_DPD_STREAK, CURRENT_DPD_STREAK_LEN, CURRENT_IS_DPD_INT.
    - Progress VELOCITY (1, real vectorized recency split, same technique
      as `engineer_installment_behavior_features()`'s LATE_RATE_TREND):
      INSTALMENT_PROGRESS_VELOCITY -- real change in mean remaining
      instalment count between the earlier and more recent halves of the
      applicant's own POS/cash history; normally negative (progressing
      toward payoff), near-zero or positive signals real stalled progress.
    - N_POS_MONTHS (1): real scope-size context for the other 7.
    """
    base = pos_cash.sort(["SK_ID_CURR", "MONTHS_BALANCE"]).with_columns([
        pl.col("SK_DPD").fill_null(0).alias("_SK_DPD"),
    ])
    base = base.with_columns([
        (pl.col("_SK_DPD") > 0).alias("_IS_DPD"),
    ])

    # --- DPD spike features: real month-over-month change within each
    # applicant's own chronologically-sorted rows. First real month has no
    # prior month to compare against -- real, disclosed edge case: filled
    # 0 (no jump measurable), not null.
    base = base.with_columns([
        (pl.col("_SK_DPD") - pl.col("_SK_DPD").shift(1).over("SK_ID_CURR")).fill_null(0).alias("_DPD_JUMP"),
    ])
    DPD_SPIKE_THRESHOLD = 5  # real, disclosed: a 5-day month-over-month DPD jump
    base = base.with_columns([
        (pl.col("_DPD_JUMP") >= DPD_SPIKE_THRESHOLD).alias("_IS_SPIKE_MONTH"),
    ])

    dpd_agg = base.group_by("SK_ID_CURR").agg([
        pl.len().alias("N_POS_MONTHS"),
        pl.col("_SK_DPD").last().alias("CURRENT_SK_DPD"),
        pl.col("_DPD_JUMP").max().alias("MAX_DPD_JUMP"),
        pl.col("_IS_SPIKE_MONTH").sum().alias("N_DPD_SPIKE_MONTHS"),
    ])

    # --- DPD streak features: same real vectorized boundary-detection +
    # cum_sum run-length encoding as `engineer_payment_streak_features()`
    # and `engineer_revolving_distress_features()`.
    base = base.with_columns([
        (pl.col("_IS_DPD") != pl.col("_IS_DPD").shift(1).over("SK_ID_CURR")).fill_null(True).alias("_NEW_STREAK"),
    ])
    base = base.with_columns([
        pl.col("_NEW_STREAK").cast(pl.Int32).cum_sum().over("SK_ID_CURR").alias("_STREAK_ID"),
    ])
    streaks = base.group_by(["SK_ID_CURR", "_STREAK_ID"]).agg([
        pl.col("_IS_DPD").first().alias("STREAK_IS_DPD"),
        pl.len().alias("STREAK_LEN"),
        pl.col("MONTHS_BALANCE").max().alias("STREAK_LAST_MONTH"),
    ])
    longest_dpd = streaks.group_by("SK_ID_CURR").agg([
        pl.col("STREAK_LEN").filter(pl.col("STREAK_IS_DPD")).max().fill_null(0).alias("LONGEST_DPD_STREAK"),
    ])
    current_dpd = (
        streaks.sort(["SK_ID_CURR", "STREAK_LAST_MONTH"])
        .group_by("SK_ID_CURR", maintain_order=True)
        .agg([
            pl.col("STREAK_IS_DPD").last().alias("_CURRENT_IS_DPD"),
            pl.col("STREAK_LEN").last().alias("CURRENT_DPD_STREAK_LEN"),
        ])
        .with_columns(pl.col("_CURRENT_IS_DPD").cast(pl.Int32).alias("CURRENT_IS_DPD_INT"))
        .select(["SK_ID_CURR", "CURRENT_IS_DPD_INT", "CURRENT_DPD_STREAK_LEN"])
    )

    # --- Instalment-progress velocity: real vectorized recency split (same
    # rank-based technique as `engineer_installment_behavior_features()`'s
    # LATE_RATE_TREND), applied to real remaining-instalment count.
    # CNT_INSTALMENT_FUTURE nulls are dropped from the MEAN only (see module
    # docstring); the final aggregated value is never left null.
    trend_base = base.with_columns([
        pl.col("MONTHS_BALANCE").rank("ordinal").over("SK_ID_CURR").alias("_RANK"),
        pl.len().over("SK_ID_CURR").alias("_N_IN_GROUP"),
    ]).with_columns([
        (pl.col("_RANK") / pl.col("_N_IN_GROUP") > 0.5).alias("_IS_RECENT_HALF"),
    ])
    half_agg = (
        trend_base.filter(pl.col("CNT_INSTALMENT_FUTURE").is_not_null())
        .group_by(["SK_ID_CURR", "_IS_RECENT_HALF"])
        .agg(pl.col("CNT_INSTALMENT_FUTURE").mean().alias("_MEAN_REMAINING"))
    )
    recent = half_agg.filter(pl.col("_IS_RECENT_HALF")).select([
        "SK_ID_CURR", pl.col("_MEAN_REMAINING").alias("_REMAIN_RECENT"),
    ])
    early = half_agg.filter(~pl.col("_IS_RECENT_HALF")).select([
        "SK_ID_CURR", pl.col("_MEAN_REMAINING").alias("_REMAIN_EARLY"),
    ])
    velocity = (
        recent.join(early, on="SK_ID_CURR", how="outer_coalesce")
        .with_columns([
            # Real, disclosed edge case: no valid CNT_INSTALMENT_FUTURE value
            # in one or both real halves -- treated as neutral 0.0 velocity
            # (no evidence of stalling or progress), never left null.
            ((pl.col("_REMAIN_RECENT") - pl.col("_REMAIN_EARLY")) / (pl.col("_REMAIN_EARLY").abs() + 1.0))
              .fill_null(0.0).alias("INSTALMENT_PROGRESS_VELOCITY"),
        ])
        .select(["SK_ID_CURR", "INSTALMENT_PROGRESS_VELOCITY"])
    )

    feat = (
        dpd_agg.join(longest_dpd, on="SK_ID_CURR", how="left")
        .join(current_dpd, on="SK_ID_CURR", how="left")
        .join(velocity, on="SK_ID_CURR", how="left")
        .with_columns(pl.col("INSTALMENT_PROGRESS_VELOCITY").fill_null(0.0))
    )

    feature_cols = [
        "N_POS_MONTHS", "CURRENT_SK_DPD", "MAX_DPD_JUMP", "N_DPD_SPIKE_MONTHS",
        "LONGEST_DPD_STREAK", "CURRENT_DPD_STREAK_LEN", "CURRENT_IS_DPD_INT",
        "INSTALMENT_PROGRESS_VELOCITY",
    ]
    return feat, feature_cols


def compute_naive_current_dpd(pos_cash: pl.DataFrame) -> pl.DataFrame:
    """Real, vectorized (WARP) NAIVE baseline for Problem 5's intervention
    ranking: each applicant's most recent real SK_DPD value from
    `POS_CASH_balance.csv` -- literally just "what is their DPD right now",
    no modeling, no engineered features. Returns a DataFrame with columns
    ["SK_ID_CURR", "NAIVE_CURRENT_DPD"]. Deliberately the simplest possible
    real comparator Problem 5 benchmarks its composite ranking against --
    see `src/features/intervention_ranking.py` for how it is used.
    """
    base = pos_cash.sort(["SK_ID_CURR", "MONTHS_BALANCE"]).with_columns([
        pl.col("SK_DPD").fill_null(0).alias("_SK_DPD"),
    ])
    return (
        base.group_by("SK_ID_CURR")
        .agg(pl.col("_SK_DPD").last().alias("NAIVE_CURRENT_DPD"))
    )
