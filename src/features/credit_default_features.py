"""
src/features/credit_default_features.py

Shared feature-engineering module for Problem 1 (Credit Default Prediction) and any
downstream notebook that needs the SAME feature set to score with Problem 1's model
(e.g. Notebook 03 / Problem 4: Credit Score Estimation).

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
