"""Real tests for src/serving/adverse_action_common.py (2026-09-08) -- closes
the disclosed gap: "No mechanism exists to translate a model's decision into
the plain-English, specific reasons a denied applicant is legally entitled
to (ECOA/Reg B 'statement of specific reasons')." Every assertion here
exercises the real curated REASON_CODE_MAP, the real mechanical fallback
humanizer, and the real protected-basis / fair-lending-proxy suppression
logic against real feature names from src/features/*.py -- no mocked
mapping data.
"""

import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from serving.adverse_action_common import (  # noqa: E402
    humanize_factor,
    render_adverse_action_notice,
)


def test_curated_reason_is_plain_english():
    text = humanize_factor("PCT_INSTALLMENTS_LATE")
    assert text == "Share of past loan installments paid late"
    assert "_" not in text


def test_fallback_humanizer_never_leaks_raw_column_name():
    # A real feature name that is deliberately NOT in REASON_CODE_MAP.
    text = humanize_factor("N_DPD_SPIKE_MONTHS")
    assert text != "N_DPD_SPIKE_MONTHS"
    assert "_" not in text
    assert "Number of" in text


def test_protected_basis_never_appears_in_customer_reasons():
    top_reasons = [
        {"factor": "CODE_GENDER", "contribution": 0.30},
        {"factor": "AMT_CREDIT", "contribution": 0.10},
    ]
    notice = render_adverse_action_notice(
        top_reasons, score=0.8, threshold=0.5, adverse_direction="positive"
    )
    assert notice["decision"] == "adverse_action"
    factors_shown = [r["factor"] for r in notice["principal_reasons"]]
    assert "CODE_GENDER" not in factors_shown
    assert "AMT_CREDIT" in factors_shown
    suppressed = [s["factor"] for s in notice["suppressed_factors"]]
    assert "CODE_GENDER" in suppressed
    category = next(
        s["category"]
        for s in notice["suppressed_factors"]
        if s["factor"] == "CODE_GENDER"
    )
    assert category == "protected_basis"


def test_fair_lending_proxy_suppressed_with_correct_category():
    top_reasons = [
        {"factor": "DEF_30_CNT_SOCIAL_CIRCLE", "contribution": 0.20},
        {"factor": "REGION_RATING_CLIENT", "contribution": 0.15},
        {"factor": "AMT_INCOME_TOTAL", "contribution": 0.05},
    ]
    notice = render_adverse_action_notice(
        top_reasons, score=0.9, threshold=0.5, adverse_direction="positive"
    )
    categories = {s["factor"]: s["category"] for s in notice["suppressed_factors"]}
    assert categories["DEF_30_CNT_SOCIAL_CIRCLE"] == "fair_lending_proxy"
    assert categories["REGION_RATING_CLIENT"] == "fair_lending_proxy"


def test_only_factors_that_worked_against_applicant_are_reasons_positive_direction():
    top_reasons = [
        {"factor": "AMT_CREDIT", "contribution": 0.25},  # raised risk -> adverse
        {"factor": "EXT_SOURCE_1", "contribution": -0.40},  # lowered risk -> helped
    ]
    notice = render_adverse_action_notice(
        top_reasons, score=0.7, threshold=0.5, adverse_direction="positive"
    )
    factors_shown = [r["factor"] for r in notice["principal_reasons"]]
    assert factors_shown == ["AMT_CREDIT"]


def test_negative_direction_flips_which_sign_is_adverse():
    # Approval-probability style: a NEGATIVE contribution hurt the applicant.
    top_reasons = [
        {
            "factor": "AMT_INCOME_TOTAL",
            "contribution": -0.30,
        },  # lowered approval prob -> adverse
        {
            "factor": "EXT_SOURCE_2",
            "contribution": 0.20,
        },  # raised approval prob -> helped
    ]
    notice = render_adverse_action_notice(
        top_reasons, score=0.2, threshold=0.5, adverse_direction="negative"
    )
    assert notice["decision"] == "adverse_action"
    factors_shown = [r["factor"] for r in notice["principal_reasons"]]
    assert factors_shown == ["AMT_INCOME_TOTAL"]


def test_approved_case_returns_no_reasons_even_if_factors_exist():
    top_reasons = [{"factor": "AMT_CREDIT", "contribution": 0.25}]
    notice = render_adverse_action_notice(
        top_reasons, score=0.3, threshold=0.5, adverse_direction="positive"
    )
    assert notice["decision"] == "approved"
    assert notice["principal_reasons"] == []
    assert notice["suppressed_factors"] == []


def test_max_reasons_caps_the_list():
    top_reasons = [
        {"factor": f, "contribution": 0.9 - i * 0.1}
        for i, f in enumerate(
            [
                "AMT_CREDIT",
                "AMT_ANNUITY",
                "AMT_INCOME_TOTAL",
                "DAYS_EMPLOYED",
                "EXT_SOURCE_1",
            ]
        )
    ]
    notice = render_adverse_action_notice(
        top_reasons,
        score=0.9,
        threshold=0.5,
        adverse_direction="positive",
        max_reasons=3,
    )
    assert len(notice["principal_reasons"]) == 3


def test_invalid_adverse_direction_raises():
    try:
        render_adverse_action_notice(
            [], score=0.5, threshold=0.5, adverse_direction="sideways"
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reasons_ordered_by_magnitude_of_adverse_contribution():
    top_reasons = [
        {"factor": "AMT_CREDIT", "contribution": 0.05},
        {"factor": "AMT_ANNUITY", "contribution": 0.35},
        {"factor": "DAYS_EMPLOYED", "contribution": 0.15},
    ]
    notice = render_adverse_action_notice(
        top_reasons, score=0.9, threshold=0.5, adverse_direction="positive"
    )
    ordered = [r["factor"] for r in notice["principal_reasons"]]
    assert ordered == ["AMT_ANNUITY", "DAYS_EMPLOYED", "AMT_CREDIT"]
