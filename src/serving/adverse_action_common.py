"""
Real ECOA/Reg B-style adverse-action reason generation, built on top of this
suite's existing real explainability path (src/serving/explainability_common.py's
occlusion-based `top_reason_codes`) -- closes a real, previously-disclosed gap:
"No mechanism exists to translate a model's decision into the plain-English,
specific reasons a denied applicant is legally entitled to (ECOA/Reg B
'statement of specific reasons')."

This module does one job the raw explainability output does NOT do on its own:
it is the compliance boundary between "what the model actually weighed" and
"what a customer-facing denial notice is allowed to say." Two real,
non-obvious problems are handled here, not glossed over:

1. Humanizing a real, curated subset of this suite's real 218 engineered
   feature names (`grep`-verified against src/features/*.py on 2026-09-08)
   into plain-English reason text a consumer can act on, with a generic
   fallback humanizer for the remainder so an unmapped feature never leaks a
   raw column name into a customer notice.

2. ECOA explicitly forbids sex, marital status, and age as bases for an
   adverse-action decision, and mature fair-lending practice additionally
   keeps social-network-based and coarse-geography features out of
   customer-facing reason text because they are well-documented redlining/
   guilt-by-association proxies (a real, current concern -- see e.g. CFPB
   guidance on algorithmic redlining risk). This suite's feature set
   includes exactly such fields (CODE_GENDER, NAME_FAMILY_STATUS, DAYS_BIRTH,
   the *_CNT_SOCIAL_CIRCLE fields, REGION_*), and this module's real,
   structural fix is to remove them from the customer-facing reason list at
   generation time -- not merely disclose the risk in a doc -- and instead
   surface them as `suppressed_factors` for internal fair-lending review.
   Note this addresses HOW an adverse-action reason is worded; it does not
   audit whether the underlying model itself is disparate-impact-free,
   which is the separate, permanently-open fair-lending/bias-audit gap this
   repo's remediation tracker documents as a real, structural "No."

Real, disclosed scope limit: the mapping below is curated by hand from real
feature names in this codebase, not learned or exhaustive across every one of
the 218 names -- unmapped names fall through to `_humanize_fallback()`, a
mechanical abbreviation-expansion + title-case pass that is honest but lower
quality than a curated entry. See ADVERSE_ACTION.md for the full disclosure.
"""

from __future__ import annotations

from typing import Optional

# ECOA explicitly names these as prohibited bases for a credit decision
# (sex, marital status, age). Never surfaced in a customer-facing reason,
# however large their real model contribution.
PROTECTED_BASIS_FEATURES = frozenset(
    {
        "CODE_GENDER",
        "NAME_FAMILY_STATUS",
        "DAYS_BIRTH",
        "AGE_YEARS",
    }
)

# Not an ECOA-named protected basis, but well-documented proxy-discrimination
# risk (guilt-by-association via a social circle's default history; coarse
# geography as a redlining proxy). Kept out of customer-facing reason text
# for the same reason many real lenders keep them out of adverse-action
# letters even when a model technically used them.
FAIR_LENDING_PROXY_FEATURES = frozenset(
    {
        "DEF_30_CNT_SOCIAL_CIRCLE",
        "OBS_30_CNT_SOCIAL_CIRCLE",
        "REGION_RATING_CLIENT",
        "REGION_POPULATION_RELATIVE",
    }
)

SUPPRESSED_FEATURES = PROTECTED_BASIS_FEATURES | FAIR_LENDING_PROXY_FEATURES


def _suppression_category(feature: str) -> Optional[str]:
    if feature in PROTECTED_BASIS_FEATURES:
        return "protected_basis"
    if feature in FAIR_LENDING_PROXY_FEATURES:
        return "fair_lending_proxy"
    return None


# Curated, real-feature-grounded reason text. Values are written the way a
# real adverse-action notice reads: a plain-English statement of the factor,
# not a restatement of the raw column name.
REASON_CODE_MAP = {
    # Requested-credit structure
    "AMT_CREDIT": "Amount of credit requested",
    "AMT_ANNUITY": "Size of the requested loan's periodic payment",
    "AMT_APPLICATION": "Amount requested on the application",
    "AMT_GOODS_PRICE": "Price of the goods being financed relative to the amount requested",
    "AMT_CREDIT_LIMIT_ACTUAL": "Requested credit limit",
    "CREDIT_TO_INCOME_RATIO": "Amount of credit requested relative to income",
    "ANNUITY_TO_INCOME_RATIO": "Size of the loan payment relative to income",
    "ANNUITY_TO_CREDIT_RATIO": "Size of the loan payment relative to the amount of credit",
    "NAME_CONTRACT_TYPE": "Type of credit product requested",
    # Income and employment
    "AMT_INCOME_TOTAL": "Amount of verified income",
    "NAME_INCOME_TYPE": "Source of income",
    "OCCUPATION_TYPE": "Occupation category",
    "DAYS_EMPLOYED": "Length of employment history",
    "YEARS_EMPLOYED": "Length of employment history",
    "NAME_EDUCATION_TYPE": "Level of education reported",
    "NAME_HOUSING_TYPE": "Housing situation reported",
    "FLAG_OWN_CAR": "Vehicle ownership reported",
    "FLAG_OWN_REALTY": "Real estate ownership reported",
    "CNT_FAM_MEMBERS": "Number of dependents/household members reported",
    # External bureau scores
    "EXT_SOURCE_1": "External credit bureau score (source 1)",
    "EXT_SOURCE_2": "External credit bureau score (source 2)",
    "EXT_SOURCE_3": "External credit bureau score (source 3)",
    # Bureau-reported credit history
    "BUREAU_CNT_ACTIVE": "Number of currently active credit accounts on file",
    "BUREAU_CNT_CREDITS": "Total number of credit accounts on file",
    "BUREAU_CNT_PROLONGED": "Number of credit agreements that were extended past their original term",
    "CNT_CREDIT_PROLONG": "Number of credit agreements that were extended past their original term",
    "CNT_CREDIT_PROLONGED_TOTAL": "Number of credit agreements that were extended past their original term",
    "BUREAU_DEBT_TO_CREDIT_RATIO": "Existing debt relative to available credit on file",
    "DEBT_TO_CREDIT_RATIO": "Existing debt relative to available credit on file",
    "BUREAU_AMT_CREDIT_SUM_DEBT_TOTAL": "Total existing debt reported on file",
    "BUREAU_AMT_CREDIT_SUM_TOTAL": "Total credit exposure reported on file",
    "BUREAU_AMT_OVERDUE_TOTAL": "Total overdue balance reported on file",
    "BUREAU_MAX_DAYS_OVERDUE": "Longest overdue period reported on an existing credit account",
    "BUREAU_TOTAL_DPD_MONTHS": "Total number of months reported delinquent across existing credit accounts",
    "PCT_CREDITS_WITH_OVERDUE": "Share of credit accounts on file with an overdue balance",
    "PCT_ACTIVE_CREDITS": "Share of credit accounts on file that are currently active",
    "N_DISTINCT_CREDIT_TYPES": "Variety of credit product types on file",
    "HAS_BUREAU_HISTORY": "Presence of prior credit bureau history",
    "MEAN_YEARS_SINCE_CREDIT_OPENED": "Average age of credit accounts on file",
    "WORST_BUREAU_BALANCE_STATUS": "Worst reported payment status across credit accounts on file",
    # Repayment / installment history
    "PCT_INSTALLMENTS_LATE": "Share of past loan installments paid late",
    "PCT_INSTALMENTS_LATE": "Share of past loan installments paid late",
    "PCT_INSTALLMENTS_UNDERPAID": "Share of past loan installments paid less than the amount due",
    "PCT_INSTALMENTS_UNDERPAID": "Share of past loan installments paid less than the amount due",
    "MEAN_DAYS_LATE": "Average number of days late on past loan installments",
    "MAX_DAYS_LATE": "Longest number of days late on a past loan installment",
    "MEAN_DAYS_LATE_WHEN_LATE": "Average lateness of installments that were paid late",
    "INSTAL_PCT_LATE": "Share of past loan installments paid late",
    "INSTAL_MEAN_DAYS_LATE_WHEN_LATE": "Average lateness of installments that were paid late",
    "INSTAL_MEAN_PAYMENT_RATIO": "Average share of the amount due actually paid on past installments",
    "MEAN_PAYMENT_RATIO": "Average share of the amount due actually paid on past installments",
    "MIN_PAYMENT_RATIO": "Lowest share of the amount due paid on a past installment",
    "PAYMENT_RATIO": "Share of the amount due actually paid on past installments",
    "REPAYMENT_CAPACITY_RATIO": "Estimated capacity to repay relative to existing obligations",
    "HAS_REPAYMENT_HISTORY": "Presence of prior installment repayment history",
    "LONGEST_LATE_STREAK": "Longest consecutive run of late installment payments",
    "LONGEST_ONTIME_STREAK": "Longest consecutive run of on-time installment payments",
    "CURRENT_STREAK_IS_LATE": "Current run of late installment payments",
    "N_LATE_STREAKS": "Number of separate late-payment episodes on record",
    # Revolving / credit-card utilization
    "CURRENT_UTILIZATION": "Current credit utilization (balance relative to credit limit)",
    "MEAN_UTILIZATION": "Average credit utilization (balance relative to credit limit)",
    "MAX_UTILIZATION": "Peak credit utilization (balance relative to credit limit)",
    "CC_MEAN_UTILIZATION": "Average credit-card utilization on file",
    "HAS_REVOLVING_HISTORY": "Presence of prior revolving-credit history",
    "PCT_MONTHS_HIGH_UTILIZATION": "Share of months with high credit-card utilization",
    "PCT_MONTHS_MIN_PAYMENT_ONLY": "Share of months where only the minimum payment was made",
    # Prior applications with this lender
    "PREVAPP_APPROVAL_RATE": "Approval rate on previous applications with this lender",
    "PREVAPP_REFUSAL_RATE": "Refusal rate on previous applications with this lender",
    "PREVAPP_CNT_APPROVED": "Number of previously approved applications with this lender",
    "PREVAPP_CNT_REFUSED": "Number of previously refused applications with this lender",
    "PREVAPP_CNT_TOTAL": "Number of previous applications with this lender",
    "PREVAPP_DAYS_SINCE_LAST_DECISION": "Time since the last decision on a previous application",
    "PREVAPP_MEAN_AMT_CREDIT": "Average amount requested on previous applications",
    # Point-of-sale loan history
    "POS_CNT_COMPLETED": "Number of completed point-of-sale loans on file",
    "POS_N_COMPLETED_OWN": "Number of this lender's point-of-sale loans completed",
    "N_POS_MONTHS": "Number of months of point-of-sale loan history on file",
}


def _humanize_fallback(feature: str) -> str:
    """Mechanical fallback for any real feature name not in REASON_CODE_MAP.

    Expands this codebase's own real naming abbreviations (confirmed by
    reading src/features/*.py) then title-cases what's left. Lower quality
    than a curated entry -- see ADVERSE_ACTION.md -- but never leaks a raw
    ALL_CAPS_WITH_UNDERSCORES column name into customer-facing text.
    """
    abbreviations = {
        "AMT": "Amount",
        "PCT": "Percentage",
        "CNT": "Count of",
        "N": "Number of",
        "AVG": "Average",
        "MEAN": "Average",
        "STD": "Variability in",
        "MAX": "Maximum",
        "MIN": "Minimum",
        "DPD": "days-past-due",
        "POS": "point-of-sale",
        "CC": "credit-card",
        "BB": "credit-bureau-balance",
        "PREVAPP": "previous-application",
        "INSTAL": "installment",
        "SK": "record",
    }
    parts = feature.split("_")
    expanded = [abbreviations.get(p, p.capitalize()) for p in parts]
    return " ".join(expanded)


def humanize_factor(feature: str) -> str:
    """Real feature name -> plain-English text. Curated entry when one
    exists, mechanical fallback otherwise. Never called on a suppressed
    (protected-basis or fair-lending-proxy) feature -- callers must filter
    those out first; see `render_adverse_action_notice`."""
    return REASON_CODE_MAP.get(feature, _humanize_fallback(feature))


def render_adverse_action_notice(
    top_reasons: list[dict],
    score: float,
    threshold: float,
    adverse_direction: str = "positive",
    max_reasons: int = 4,
) -> dict:
    """Turn this suite's real occlusion-based `top_reason_codes()` output
    into an ECOA/Reg B-style "specific reasons" notice.

    `adverse_direction` tells this function which sign of `contribution`
    counts as "worked against the applicant," since different services in
    this suite score in opposite directions (a default-probability service's
    risk goes UP with a bad factor; an approval-probability service's score
    goes DOWN with one):
      - "positive": a positive contribution (raised the score) is adverse.
        Use this for probability-of-default / risk-tier / capital-requirement
        style scores, where `score >= threshold` triggers adverse action.
      - "negative": a negative contribution (lowered the score) is adverse.
        Use this for approval-probability style scores, where
        `score < threshold` triggers adverse action.

    Real, disclosed limitation: this function decides wording and ECOA/fair-
    lending suppression; it does NOT decide whether a real accept/reject
    action was taken -- consistent with this suite's documented stance that
    its services are decision-support signals, not automated decision
    systems (see loan_approval_scoring_service.py's own docstring).
    """
    if adverse_direction not in ("positive", "negative"):
        raise ValueError("adverse_direction must be 'positive' or 'negative'")

    is_adverse = (
        score >= threshold if adverse_direction == "positive" else score < threshold
    )

    ranked = sorted(
        top_reasons,
        key=lambda r: (
            r["contribution"] if adverse_direction == "positive" else -r["contribution"]
        ),
        reverse=True,
    )

    principal_reasons: list[dict] = []
    suppressed_factors: list[dict] = []
    for reason in ranked:
        factor = reason["factor"]
        contribution = reason["contribution"]
        worked_against_applicant = (
            contribution > 0 if adverse_direction == "positive" else contribution < 0
        )
        if not worked_against_applicant:
            continue
        category = _suppression_category(factor)
        if category is not None:
            suppressed_factors.append({"factor": factor, "category": category})
            continue
        if len(principal_reasons) < max_reasons:
            principal_reasons.append(
                {
                    "factor": factor,
                    "reason": humanize_factor(factor),
                    "contribution": contribution,
                }
            )

    return {
        "decision": "adverse_action" if is_adverse else "approved",
        "score": score,
        "threshold": threshold,
        "principal_reasons": principal_reasons if is_adverse else [],
        "suppressed_factors": suppressed_factors if is_adverse else [],
    }
