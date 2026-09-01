"""
src/features/applicant_credit_history_features.py

Shared, real-data feature-engineering module that turns the 5 supplementary Home
Credit tables (bureau, bureau_balance, POS_CASH_balance, installments_payments,
credit_card_balance) into applicant-level (SK_ID_CURR) features.

Built once, imported everywhere (HYPER standing rule) -- any notebook that needs a
richer applicant credit-history profile imports this, rather than re-deriving the
same aggregations inline.

Two functions, because the 5 tables split into two genuinely different leakage
situations:

1. `engineer_bureau_history_features(bureau, bureau_balance)` -- bureau data comes
   from an EXTERNAL credit bureau, entirely independent of Home Credit's own
   previous_application decisions. It carries no SK_ID_PREV linkage to any specific
   Home Credit loan, so it is always safe to use in full, at SK_ID_CURR level,
   regardless of what granularity the notebook's TARGET is defined at. (This is the
   exact convention already used, and accepted, by Notebook 01 / Problem 1.)

2. `engineer_prev_loan_servicing_features_loo(pos_cash, installments, credit_card)`
   -- POS_CASH_balance, installments_payments, and credit_card_balance are each
   keyed to a specific previous_application row (SK_ID_PREV), and only contain
   servicing records for loans that were actually disbursed. A notebook whose
   TARGET is "was THIS previous_application row approved" (e.g. Notebook 02 /
   Problem 2) cannot safely fold a row's own servicing history into its own
   feature set -- that would leak the very approval outcome being predicted, and
   a naive per-applicant aggregate has exactly this problem whenever an applicant
   has more than one in-scope previous application. This function returns BOTH
   the applicant-level TOTAL (summed across every SK_ID_PREV for that applicant)
   and the per-SK_ID_PREV OWN contribution, as pure counts and sums (never a
   pre-divided mean, so the two are subtraction-compatible: TOTAL - OWN = a
   correct leave-one-out (LOO) aggregate over every OTHER previous application
   that same applicant has). The caller joins both onto its row-level frame,
   subtracts, and derives any final ratios itself -- see Notebook 02's own
   Section 6 for the worked example. A notebook whose TARGET is at SK_ID_CURR
   level (no single row to leave out) can simply use the TOTAL block untouched.
"""
import polars as pl


def engineer_bureau_history_features(bureau: pl.DataFrame, bureau_balance: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP) bureau + bureau_balance aggregation to one row per
    SK_ID_CURR. Safe to join in full onto any target granularity (see module docstring)."""
    bb_agg = (
        bureau_balance.group_by("SK_ID_BUREAU")
        .agg([
            pl.len().alias("BB_N_MONTHS"),
            pl.col("STATUS").is_in(["1", "2", "3", "4", "5"]).sum().alias("BB_N_DPD_MONTHS"),
        ])
    )
    bureau_with_bb = bureau.join(bb_agg, on="SK_ID_BUREAU", how="left").with_columns([
        pl.col("BB_N_MONTHS").fill_null(0),
        pl.col("BB_N_DPD_MONTHS").fill_null(0),
    ])
    bureau_agg = (
        bureau_with_bb.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("BUREAU_CNT_CREDITS"),
            (pl.col("CREDIT_ACTIVE") == "Active").sum().alias("BUREAU_CNT_ACTIVE"),
            pl.col("AMT_CREDIT_SUM").sum().alias("BUREAU_AMT_CREDIT_SUM_TOTAL"),
            pl.col("AMT_CREDIT_SUM_DEBT").sum().alias("BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL"),
            pl.col("CREDIT_DAY_OVERDUE").max().alias("BUREAU_MAX_DAYS_OVERDUE"),
            pl.col("BB_N_DPD_MONTHS").sum().alias("BUREAU_TOTAL_DPD_MONTHS"),
        ])
        .with_columns(
            (pl.col("BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL") / (pl.col("BUREAU_AMT_CREDIT_SUM_TOTAL") + 1.0))
            .alias("BUREAU_DEBT_TO_CREDIT_RATIO")
        )
    )
    feature_names = [c for c in bureau_agg.columns if c != "SK_ID_CURR"]
    bureau_agg = bureau_agg.with_columns([pl.col(c).fill_null(0) for c in feature_names])
    return bureau_agg, feature_names


def engineer_prev_loan_servicing_features_loo(
    pos_cash: pl.DataFrame, installments: pl.DataFrame, credit_card: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame, list[str]]:
    """Real, vectorized (WARP) POS_CASH_balance / installments_payments /
    credit_card_balance aggregation, split into an applicant-level TOTAL block
    (keyed SK_ID_CURR) and a per-application OWN block (keyed SK_ID_PREV) -- pure
    counts and sums only, so a caller can compute an exact leave-one-out aggregate
    via TOTAL - OWN. See module docstring for why this split exists.
    """
    pos_prev = (
        pos_cash.group_by("SK_ID_PREV")
        .agg([
            pl.len().alias("POS_N_OWN"),
            (pl.col("NAME_CONTRACT_STATUS") == "Completed").sum().alias("POS_N_COMPLETED_OWN"),
            pl.col("SK_DPD").sum().alias("POS_SUM_SK_DPD_OWN"),
            pl.col("SK_DPD_DEF").sum().alias("POS_SUM_SK_DPD_DEF_OWN"),
        ])
    )
    pos_curr = (
        pos_cash.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("POS_N_TOT"),
            (pl.col("NAME_CONTRACT_STATUS") == "Completed").sum().alias("POS_N_COMPLETED_TOT"),
            pl.col("SK_DPD").sum().alias("POS_SUM_SK_DPD_TOT"),
            pl.col("SK_DPD_DEF").sum().alias("POS_SUM_SK_DPD_DEF_TOT"),
        ])
    )

    inst_prev = (
        installments.with_columns([
            (pl.col("AMT_PAYMENT") / (pl.col("AMT_INSTALMENT") + 1.0)).alias("_pr"),
            (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT")).alias("_dl"),
        ])
        .group_by("SK_ID_PREV")
        .agg([
            pl.len().alias("INSTAL_N_OWN"),
            pl.col("_pr").sum().alias("INSTAL_SUM_PAY_RATIO_OWN"),
            (pl.col("_dl") > 0).sum().alias("INSTAL_N_LATE_OWN"),
            pl.col("_dl").filter(pl.col("_dl") > 0).sum().alias("INSTAL_SUM_DAYS_LATE_OWN"),
        ])
        .with_columns(pl.col("INSTAL_SUM_DAYS_LATE_OWN").fill_null(0.0))
    )
    inst_curr = (
        installments.with_columns([
            (pl.col("AMT_PAYMENT") / (pl.col("AMT_INSTALMENT") + 1.0)).alias("_pr"),
            (pl.col("DAYS_ENTRY_PAYMENT") - pl.col("DAYS_INSTALMENT")).alias("_dl"),
        ])
        .group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("INSTAL_N_TOT"),
            pl.col("_pr").sum().alias("INSTAL_SUM_PAY_RATIO_TOT"),
            (pl.col("_dl") > 0).sum().alias("INSTAL_N_LATE_TOT"),
            pl.col("_dl").filter(pl.col("_dl") > 0).sum().alias("INSTAL_SUM_DAYS_LATE_TOT"),
        ])
        .with_columns(pl.col("INSTAL_SUM_DAYS_LATE_TOT").fill_null(0.0))
    )

    cc_prev = (
        credit_card.with_columns(
            (pl.col("AMT_BALANCE") / (pl.col("AMT_CREDIT_LIMIT_ACTUAL") + 1.0)).alias("_ut")
        )
        .group_by("SK_ID_PREV")
        .agg([
            pl.len().alias("CC_N_OWN"),
            pl.col("_ut").sum().alias("CC_SUM_UTILIZATION_OWN"),
            pl.col("AMT_BALANCE").sum().alias("CC_SUM_BALANCE_OWN"),
            pl.col("SK_DPD").sum().alias("CC_SUM_SK_DPD_OWN"),
        ])
    )
    cc_curr = (
        credit_card.with_columns(
            (pl.col("AMT_BALANCE") / (pl.col("AMT_CREDIT_LIMIT_ACTUAL") + 1.0)).alias("_ut")
        )
        .group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("CC_N_TOT"),
            pl.col("_ut").sum().alias("CC_SUM_UTILIZATION_TOT"),
            pl.col("AMT_BALANCE").sum().alias("CC_SUM_BALANCE_TOT"),
            pl.col("SK_DPD").sum().alias("CC_SUM_SK_DPD_TOT"),
        ])
    )

    all_curr_ids = (
        pos_curr.select("SK_ID_CURR").vstack(inst_curr.select("SK_ID_CURR")).vstack(cc_curr.select("SK_ID_CURR")).unique()
    )
    totals_df = (
        all_curr_ids.join(pos_curr, on="SK_ID_CURR", how="left")
        .join(inst_curr, on="SK_ID_CURR", how="left")
        .join(cc_curr, on="SK_ID_CURR", how="left")
    )
    tot_cols = [c for c in totals_df.columns if c != "SK_ID_CURR"]
    totals_df = totals_df.with_columns([pl.col(c).fill_null(0) for c in tot_cols])

    all_prev_ids = (
        pos_prev.select("SK_ID_PREV").vstack(inst_prev.select("SK_ID_PREV")).vstack(cc_prev.select("SK_ID_PREV")).unique()
    )
    own_df = (
        all_prev_ids.join(pos_prev, on="SK_ID_PREV", how="left")
        .join(inst_prev, on="SK_ID_PREV", how="left")
        .join(cc_prev, on="SK_ID_PREV", how="left")
    )
    own_cols = [c for c in own_df.columns if c != "SK_ID_PREV"]
    own_df = own_df.with_columns([pl.col(c).fill_null(0) for c in own_cols])

    # Final feature names the caller will end up with after LOO subtraction + ratio derivation.
    feature_names = [
        "POS_CNT_RECORDS", "POS_CNT_COMPLETED", "POS_MEAN_SK_DPD_DEF",
        "INSTAL_CNT_PAYMENTS", "INSTAL_MEAN_PAYMENT_RATIO", "INSTAL_PCT_LATE", "INSTAL_MEAN_DAYS_LATE_WHEN_LATE",
        "CC_CNT_RECORDS", "CC_MEAN_UTILIZATION", "CC_MEAN_BALANCE", "CC_SUM_SK_DPD",
    ]
    return totals_df, own_df, feature_names


def engineer_previous_application_features(previous_application: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """Real, vectorized (WARP) `previous_application.csv` aggregation to one row
    per SK_ID_CURR -- an applicant's own history of PAST Home Credit applications
    (approved, refused, cancelled, unused-offer), as opposed to bureau.csv's
    EXTERNAL credit history or POS/installments/credit_card's loan-SERVICING
    history (both already covered by the two functions above in this module).

    Leakage note: every row in `previous_application.csv` is a COMPLETED past
    decision (Home Credit's own historical Approved/Refused/Cancelled/Unused
    offer outcome on a PRIOR application) -- there is no SK_ID_PREV linkage to
    whatever NEW application a downstream notebook's TARGET is about, so this is
    safe to use in full, at SK_ID_CURR level, for any notebook in this suite
    (the same convention `engineer_bureau_history_features` already documents for
    bureau.csv, extended here to Home Credit's own application history).

    Returns (agg, feature_names) where agg has one row per SK_ID_CURR with
    `feature_names` (all null-filled to 0 already)."""
    agg = (
        previous_application.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("PREVAPP_CNT_TOTAL"),
            (pl.col("NAME_CONTRACT_STATUS") == "Approved").sum().alias("PREVAPP_CNT_APPROVED"),
            (pl.col("NAME_CONTRACT_STATUS") == "Refused").sum().alias("PREVAPP_CNT_REFUSED"),
            pl.col("AMT_APPLICATION").mean().alias("PREVAPP_MEAN_AMT_APPLICATION"),
            pl.col("AMT_CREDIT").mean().alias("PREVAPP_MEAN_AMT_CREDIT"),
            pl.col("AMT_ANNUITY").mean().alias("PREVAPP_MEAN_AMT_ANNUITY"),
            pl.col("DAYS_DECISION").max().alias("PREVAPP_DAYS_SINCE_LAST_DECISION"),
        ])
        .with_columns([
            (pl.col("PREVAPP_CNT_APPROVED") / (pl.col("PREVAPP_CNT_TOTAL") + 1.0)).alias("PREVAPP_APPROVAL_RATE"),
            (pl.col("PREVAPP_CNT_REFUSED") / (pl.col("PREVAPP_CNT_TOTAL") + 1.0)).alias("PREVAPP_REFUSAL_RATE"),
        ])
    )
    feature_names = [c for c in agg.columns if c != "SK_ID_CURR"]
    agg = agg.with_columns([pl.col(c).fill_null(0) for c in feature_names])
    return agg, feature_names
