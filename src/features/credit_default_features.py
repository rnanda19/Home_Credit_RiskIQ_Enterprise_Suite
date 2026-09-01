"""
src/features/credit_default_features.py

Shared feature-engineering module for Problem 1 (Credit Default Prediction) and any
downstream notebook that needs the SAME feature set to score with Problem 1's model
(e.g. Notebook 03 / Problem 3: Credit Score Estimation).

Built once, imported everywhere (HYPER standing rule) -- this is the module Notebook 01
and Notebook 03 both import, instead of each notebook carrying its own inline copy of
this logic.
"""
import polars as pl


def engineer_credit_default_features(app: pl.DataFrame, bureau: pl.DataFrame):
    """Real, vectorized (WARP) feature engineering shared by Problem 1's training
    notebook and any downstream notebook that scores with Problem 1's model.

    Returns (df, numeric_features, categorical_features) where df has columns
    ["SK_ID_CURR"] + (["TARGET"] if present in app) + numeric_features + categorical_features.
    """
    bureau_agg = (
        bureau.group_by("SK_ID_CURR")
        .agg([
            pl.len().alias("BUREAU_CNT_CREDITS"),
            (pl.col("CREDIT_ACTIVE") == "Active").sum().alias("BUREAU_CNT_ACTIVE"),
            pl.col("AMT_CREDIT_SUM").sum().alias("BUREAU_AMT_CREDIT_SUM_TOTAL"),
            pl.col("AMT_CREDIT_SUM_DEBT").sum().alias("BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL"),
            pl.col("AMT_CREDIT_SUM_OVERDUE").sum().alias("BUREAU_AMT_OVERDUE_TOTAL"),
            pl.col("CREDIT_DAY_OVERDUE").max().alias("BUREAU_MAX_DAYS_OVERDUE"),
            pl.col("DAYS_CREDIT").min().alias("BUREAU_DAYS_CREDIT_MIN"),
            pl.col("CNT_CREDIT_PROLONG").sum().alias("BUREAU_CNT_PROLONGED"),
        ])
    )
    bureau_agg = bureau_agg.with_columns(
        (pl.col("BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL") / (pl.col("BUREAU_AMT_CREDIT_SUM_TOTAL") + 1.0))
        .alias("BUREAU_DEBT_TO_CREDIT_RATIO")
    )

    df = app.join(bureau_agg, on="SK_ID_CURR", how="left")
    bureau_feature_cols = [c for c in bureau_agg.columns if c != "SK_ID_CURR"]
    df = df.with_columns([pl.col(c).fill_null(0) for c in bureau_feature_cols])

    df = df.with_columns([
        (-pl.col("DAYS_BIRTH") / 365.25).alias("AGE_YEARS"),
        pl.when(pl.col("DAYS_EMPLOYED") == 365243).then(None).otherwise(-pl.col("DAYS_EMPLOYED") / 365.25)
          .alias("YEARS_EMPLOYED"),
        (pl.col("AMT_CREDIT") / (pl.col("AMT_INCOME_TOTAL") + 1.0)).alias("CREDIT_TO_INCOME_RATIO"),
        (pl.col("AMT_ANNUITY") / (pl.col("AMT_INCOME_TOTAL") + 1.0)).alias("ANNUITY_TO_INCOME_RATIO"),
        (pl.col("AMT_ANNUITY") / (pl.col("AMT_CREDIT") + 1.0)).alias("ANNUITY_TO_CREDIT_RATIO"),
    ])

    numeric_features = [c for c in [
        "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE",
        "REGION_POPULATION_RELATIVE", "AGE_YEARS", "YEARS_EMPLOYED", "CNT_CHILDREN",
        "CNT_FAM_MEMBERS", "CREDIT_TO_INCOME_RATIO", "ANNUITY_TO_INCOME_RATIO",
        "ANNUITY_TO_CREDIT_RATIO", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
        "OBS_30_CNT_SOCIAL_CIRCLE", "DEF_30_CNT_SOCIAL_CIRCLE", "DAYS_LAST_PHONE_CHANGE",
        "AMT_REQ_CREDIT_BUREAU_YEAR", "REGION_RATING_CLIENT",
    ] + bureau_feature_cols if c in df.columns]
    categorical_features = [c for c in [
        "NAME_CONTRACT_TYPE", "CODE_GENDER", "FLAG_OWN_CAR", "FLAG_OWN_REALTY",
        "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE", "NAME_FAMILY_STATUS",
        "NAME_HOUSING_TYPE", "OCCUPATION_TYPE",
    ] if c in df.columns]

    keep_cols = ["SK_ID_CURR"] + (["TARGET"] if "TARGET" in df.columns else []) + numeric_features + categorical_features
    return df.select(keep_cols), numeric_features, categorical_features


def engineer_credit_default_features_v2(
    app: pl.DataFrame,
    bureau: pl.DataFrame,
    bureau_balance: pl.DataFrame,
    previous_application: pl.DataFrame,
    pos_cash: pl.DataFrame,
    installments: pl.DataFrame,
    credit_card: pl.DataFrame,
):
    """Real, vectorized (WARP) feature engineering for Problem 1, v2 -- adds the
    5 real Home Credit tables `engineer_credit_default_features` (v1) did not use
    (bureau_balance, previous_application, POS_CASH_balance,
    installments_payments, credit_card_balance), on top of v1's real application +
    bureau fields. Reuses the shared, already-leakage-checked
    `src/features/applicant_credit_history_features.py` module for all 5 rather
    than re-deriving any of this logic inline (HYPER).

    Why v2 exists (zero-fabrication disclosure): v1 trained Problem 1's champion
    model on only 2 of Home Credit's 7 real data tables. The other 5 carry real
    BEHAVIORAL signal (past repayment conduct, past approval/refusal history,
    revolving-credit usage) that application-snapshot fields alone cannot
    capture, and which the actual Home Credit Default Risk competition's public
    solutions consistently show materially improves default prediction over an
    application-only baseline. v2 was built, and the champion model retrained
    against it, specifically because a 2-table model understates achievable
    accuracy for every downstream Mega Project that reuses Problem 1's PD output
    (this is a deliberate accuracy fix, not a routine feature addition -- see
    CHANGELOG.md for the measured before/after holdout AUC comparison).

    Leakage handling (why each source is safe to use in full, at SK_ID_CURR level):
      - bureau + bureau_balance: EXTERNAL credit bureau data, no linkage to any
        Home Credit loan of any kind. Safe in full (same as v1).
      - previous_application: Home Credit's own PAST, COMPLETED application
        decisions (Approved/Refused/Cancelled/Unused offer) -- these are already-
        resolved historical outcomes, not the new application this model scores.
        Safe in full at SK_ID_CURR level (see
        `engineer_previous_application_features`'s own docstring).
      - POS_CASH_balance / installments_payments / credit_card_balance: real
        SERVICING history on an applicant's past DISBURSED loans. This function
        uses only the applicant-level TOTAL block from
        `engineer_prev_loan_servicing_features_loo` (no leave-one-out
        subtraction) -- correct and safe here specifically because Problem 1's
        TARGET is "will THIS NEW application default", which has no SK_ID_PREV of
        its own in these servicing tables, so there is nothing to leave out (this
        is the exact case that module's own docstring describes: "a notebook
        whose TARGET is at SK_ID_CURR level ... can simply use the TOTAL block
        untouched"). Problem 2 (Notebook 02), by contrast, predicts the outcome of
        a SPECIFIC previous_application row and therefore DOES need the
        leave-one-out subtraction that module also provides -- that usage is
        unchanged by this function's addition.

    Returns (df, numeric_features, categorical_features) -- same shape as v1's
    return, so every existing caller pattern (`df, NUMERIC, CATEGORICAL =
    engineer_credit_default_features_v2(...)`) is a drop-in replacement for v1.
    """
    from features.applicant_credit_history_features import (
        engineer_bureau_history_features, engineer_prev_loan_servicing_features_loo,
        engineer_previous_application_features,
    )

    bureau_agg, bureau_feature_cols = engineer_bureau_history_features(bureau, bureau_balance)
    prevapp_agg, prevapp_feature_cols = engineer_previous_application_features(previous_application)
    servicing_totals_df, _servicing_own_df, _servicing_feature_names = engineer_prev_loan_servicing_features_loo(
        pos_cash, installments, credit_card
    )

    df = app.join(bureau_agg, on="SK_ID_CURR", how="left")
    df = df.join(prevapp_agg, on="SK_ID_CURR", how="left")
    df = df.join(servicing_totals_df, on="SK_ID_CURR", how="left")

    df = df.with_columns([pl.col(c).fill_null(0) for c in bureau_feature_cols + prevapp_feature_cols])
    _servicing_tot_cols = [c for c in servicing_totals_df.columns if c != "SK_ID_CURR"]
    df = df.with_columns([pl.col(c).fill_null(0) for c in _servicing_tot_cols])

    # Derive the same ratio-style servicing features Notebook 02 (Problem 2)
    # derives from its LOO-subtracted values -- here from the TOTAL-only block,
    # which is the correct, leakage-safe choice at this notebook's SK_ID_CURR
    # target granularity (see docstring above).
    df = df.with_columns([
        pl.col("POS_N_TOT").alias("POS_CNT_RECORDS"),
        pl.col("POS_N_COMPLETED_TOT").alias("POS_CNT_COMPLETED"),
        (pl.col("POS_SUM_SK_DPD_DEF_TOT") / (pl.col("POS_N_TOT") + 1.0)).alias("POS_MEAN_SK_DPD_DEF"),
        pl.col("INSTAL_N_TOT").alias("INSTAL_CNT_PAYMENTS"),
        (pl.col("INSTAL_SUM_PAY_RATIO_TOT") / (pl.col("INSTAL_N_TOT") + 1.0)).alias("INSTAL_MEAN_PAYMENT_RATIO"),
        (pl.col("INSTAL_N_LATE_TOT") / (pl.col("INSTAL_N_TOT") + 1.0)).alias("INSTAL_PCT_LATE"),
        (pl.col("INSTAL_SUM_DAYS_LATE_TOT") / (pl.col("INSTAL_N_LATE_TOT") + 1.0)).alias("INSTAL_MEAN_DAYS_LATE_WHEN_LATE"),
        pl.col("CC_N_TOT").alias("CC_CNT_RECORDS"),
        (pl.col("CC_SUM_UTILIZATION_TOT") / (pl.col("CC_N_TOT") + 1.0)).alias("CC_MEAN_UTILIZATION"),
        (pl.col("CC_SUM_BALANCE_TOT") / (pl.col("CC_N_TOT") + 1.0)).alias("CC_MEAN_BALANCE"),
        pl.col("CC_SUM_SK_DPD_TOT").alias("CC_SUM_SK_DPD"),
    ])
    servicing_derived_cols = [
        "POS_CNT_RECORDS", "POS_CNT_COMPLETED", "POS_MEAN_SK_DPD_DEF",
        "INSTAL_CNT_PAYMENTS", "INSTAL_MEAN_PAYMENT_RATIO", "INSTAL_PCT_LATE", "INSTAL_MEAN_DAYS_LATE_WHEN_LATE",
        "CC_CNT_RECORDS", "CC_MEAN_UTILIZATION", "CC_MEAN_BALANCE", "CC_SUM_SK_DPD",
    ]
    df = df.with_columns([pl.col(c).fill_null(0) for c in servicing_derived_cols])

    df = df.with_columns([
        (-pl.col("DAYS_BIRTH") / 365.25).alias("AGE_YEARS"),
        pl.when(pl.col("DAYS_EMPLOYED") == 365243).then(None).otherwise(-pl.col("DAYS_EMPLOYED") / 365.25)
          .alias("YEARS_EMPLOYED"),
        (pl.col("AMT_CREDIT") / (pl.col("AMT_INCOME_TOTAL") + 1.0)).alias("CREDIT_TO_INCOME_RATIO"),
        (pl.col("AMT_ANNUITY") / (pl.col("AMT_INCOME_TOTAL") + 1.0)).alias("ANNUITY_TO_INCOME_RATIO"),
        (pl.col("AMT_ANNUITY") / (pl.col("AMT_CREDIT") + 1.0)).alias("ANNUITY_TO_CREDIT_RATIO"),
    ])

    numeric_features = [c for c in [
        "AMT_INCOME_TOTAL", "AMT_CREDIT", "AMT_ANNUITY", "AMT_GOODS_PRICE",
        "REGION_POPULATION_RELATIVE", "AGE_YEARS", "YEARS_EMPLOYED", "CNT_CHILDREN",
        "CNT_FAM_MEMBERS", "CREDIT_TO_INCOME_RATIO", "ANNUITY_TO_INCOME_RATIO",
        "ANNUITY_TO_CREDIT_RATIO", "EXT_SOURCE_1", "EXT_SOURCE_2", "EXT_SOURCE_3",
        "OBS_30_CNT_SOCIAL_CIRCLE", "DEF_30_CNT_SOCIAL_CIRCLE", "DAYS_LAST_PHONE_CHANGE",
        "AMT_REQ_CREDIT_BUREAU_YEAR", "REGION_RATING_CLIENT",
    ] + bureau_feature_cols + prevapp_feature_cols + servicing_derived_cols if c in df.columns]
    categorical_features = [c for c in [
        "NAME_CONTRACT_TYPE", "CODE_GENDER", "FLAG_OWN_CAR", "FLAG_OWN_REALTY",
        "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE", "NAME_FAMILY_STATUS",
        "NAME_HOUSING_TYPE", "OCCUPATION_TYPE",
    ] if c in df.columns]

    keep_cols = ["SK_ID_CURR"] + (["TARGET"] if "TARGET" in df.columns else []) + numeric_features + categorical_features
    return df.select(keep_cols), numeric_features, categorical_features
