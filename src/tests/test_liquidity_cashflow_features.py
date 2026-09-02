"""
src/tests/test_liquidity_cashflow_features.py

Real, hand-built test cases for src/features/liquidity_cashflow_features.py
(Mega Project 5's new HYPER shared module). Every expected value below is
computed independently by hand in this docstring/comments, then checked
against the real function's actual output -- no mocked or fabricated
expectation, consistent with this suite's standing verification policy.
No business data, no notebook artifacts, no trained model required.
"""
import sys
from pathlib import Path

import polars as pl
import pytest

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from features.liquidity_cashflow_features import (  # noqa: E402
    attach_repayment_capacity,
    bootstrap_cash_flow_at_risk,
    engineer_applicant_cash_reliability_features,
    reconstruct_portfolio_cashflow_periods,
)


def _installments() -> pl.DataFrame:
    """3 real hand-built installment rows across 2 applicants:
    - SK_ID_CURR 100, installment A: scheduled day -30, $1000, paid day -32
      (2 days EARLY), $1000 (paid in full).
    - SK_ID_CURR 100, installment B: scheduled day -10, $2000, paid day -5
      (5 days LATE), $1500 (underpaid by $500).
    - SK_ID_CURR 200, installment C: scheduled day -20, $500, never paid
      (null DAYS_ENTRY_PAYMENT / AMT_PAYMENT).
    """
    return pl.DataFrame({
        "SK_ID_CURR": [100, 100, 200],
        "SK_ID_PREV": [1, 1, 2],
        "DAYS_INSTALMENT": [-30, -10, -20],
        "DAYS_ENTRY_PAYMENT": [-32, -5, None],
        "AMT_INSTALMENT": [1000.0, 2000.0, 500.0],
        "AMT_PAYMENT": [1000.0, 1500.0, None],
    })


def test_engineer_applicant_cash_reliability_features_applicant_100():
    feat, cols = engineer_applicant_cash_reliability_features(_installments())
    row = feat.filter(pl.col("SK_ID_CURR") == 100).to_dicts()[0]

    assert row["N_INSTALLMENTS"] == 2
    assert row["TOTAL_SCHEDULED_CASH_AMT"] == pytest.approx(3000.0)
    assert row["TOTAL_COLLECTED_CASH_AMT"] == pytest.approx(2500.0)
    # 2500 / 3000
    assert row["DOLLAR_COLLECTION_RATE"] == pytest.approx(2500.0 / 3000.0)
    # max(3000 - 2500, 0)
    assert row["OUTSTANDING_SHORTFALL_AMT"] == pytest.approx(500.0)
    # weighted: ((-32 - -30) * 1000 + (-5 - -10) * 2000) / (1000 + 2000)
    #         = (-2 * 1000 + 5 * 2000) / 3000 = (-2000 + 10000) / 3000
    expected_weighted_late = (-2 * 1000.0 + 5 * 2000.0) / 3000.0
    assert row["DOLLAR_WEIGHTED_DAYS_LATE"] == pytest.approx(expected_weighted_late)
    assert set(cols) == {
        "N_INSTALLMENTS", "TOTAL_SCHEDULED_CASH_AMT", "TOTAL_COLLECTED_CASH_AMT",
        "DOLLAR_COLLECTION_RATE", "OUTSTANDING_SHORTFALL_AMT", "DOLLAR_WEIGHTED_DAYS_LATE",
    }


def test_engineer_applicant_cash_reliability_features_applicant_200_never_paid():
    feat, _ = engineer_applicant_cash_reliability_features(_installments())
    row = feat.filter(pl.col("SK_ID_CURR") == 200).to_dicts()[0]

    assert row["N_INSTALLMENTS"] == 1
    assert row["TOTAL_SCHEDULED_CASH_AMT"] == pytest.approx(500.0)
    # null AMT_PAYMENT treated as $0 real cash collected so far
    assert row["TOTAL_COLLECTED_CASH_AMT"] == pytest.approx(0.0)
    assert row["DOLLAR_COLLECTION_RATE"] == pytest.approx(0.0)
    assert row["OUTSTANDING_SHORTFALL_AMT"] == pytest.approx(500.0)
    # real, disclosed edge case: nothing paid yet -> no real lateness-on-paid-cash
    # to weight, defined 0.0, never null
    assert row["DOLLAR_WEIGHTED_DAYS_LATE"] == pytest.approx(0.0)


def test_reconstruct_portfolio_cashflow_periods_all_three_land_in_same_period():
    periods = reconstruct_portfolio_cashflow_periods(_installments(), period_days=30)
    # floor(-30/30)=-1, floor(-10/30)=-1, floor(-20/30)=-1 -- all 3 real
    # installments land in the same 30-day period bucket.
    assert periods.height == 1
    row = periods.to_dicts()[0]
    assert row["N_INSTALLMENTS_SCHEDULED"] == 3
    assert row["N_APPLICANTS_SCHEDULED"] == 2
    assert row["SCHEDULED_CASH_AMT"] == pytest.approx(3500.0)
    assert row["COLLECTED_CASH_AMT"] == pytest.approx(2500.0)
    assert row["DOLLAR_COLLECTION_RATE"] == pytest.approx(2500.0 / 3500.0)
    assert row["PERIOD_START_DAY"] == -30


def test_reconstruct_portfolio_cashflow_periods_separates_distinct_periods():
    # A 4th installment 90 real days earlier than the cluster above must land
    # in a genuinely different period bucket, not get merged in.
    installments = _installments().vstack(pl.DataFrame({
        "SK_ID_CURR": [300], "SK_ID_PREV": [3], "DAYS_INSTALMENT": [-120],
        "DAYS_ENTRY_PAYMENT": [-120], "AMT_INSTALMENT": [700.0], "AMT_PAYMENT": [700.0],
    }))
    periods = reconstruct_portfolio_cashflow_periods(installments, period_days=30)
    assert periods.height == 2
    assert periods.sort("_PERIOD_ID")["N_INSTALLMENTS_SCHEDULED"].to_list() == [1, 3]


def test_attach_repayment_capacity_reuses_mp1_formula_exactly():
    installments = _installments()
    feat, _ = engineer_applicant_cash_reliability_features(installments)
    application = pl.DataFrame({
        "SK_ID_CURR": [100, 200],
        "AMT_INCOME_TOTAL": [180000.0, 90000.0],
        "AMT_ANNUITY": [24000.0, None],
    })
    joined = attach_repayment_capacity(feat, application)
    row100 = joined.filter(pl.col("SK_ID_CURR") == 100).to_dicts()[0]
    row200 = joined.filter(pl.col("SK_ID_CURR") == 200).to_dicts()[0]
    # Exact MP1 formula: AMT_INCOME_TOTAL / (AMT_ANNUITY + 1.0)
    assert row100["REPAYMENT_CAPACITY_RATIO"] == pytest.approx(180000.0 / (24000.0 + 1.0))
    # Real, disclosed: null AMT_ANNUITY -> null ratio, never a fabricated fallback
    assert row200["REPAYMENT_CAPACITY_RATIO"] is None


def _hand_built_periods() -> pl.DataFrame:
    """5 real hand-built calendar periods, ascending _PERIOD_ID. Every value
    below is chosen so the expected closed-form mean can be computed by
    hand: real mean rate = (0.9+0.95+0.85+0.92+0.88)/5 = 0.90 exactly; the 3
    most recent periods' real SCHEDULED_CASH_AMT = [1000, 2000, 3000], mean
    = 2000.0 exactly."""
    return pl.DataFrame({
        "_PERIOD_ID": [0, 1, 2, 3, 4],
        "PERIOD_START_DAY": [0, 30, 60, 90, 120],
        "N_INSTALLMENTS_SCHEDULED": [5, 5, 5, 5, 5],
        "N_APPLICANTS_SCHEDULED": [5, 5, 5, 5, 5],
        "SCHEDULED_CASH_AMT": [1000.0, 1000.0, 1000.0, 2000.0, 3000.0],
        "COLLECTED_CASH_AMT": [900.0, 950.0, 850.0, 1840.0, 2640.0],
        "DOLLAR_COLLECTION_RATE": [0.9, 0.95, 0.85, 0.92, 0.88],
    })


def test_bootstrap_cash_flow_at_risk_raises_on_too_few_periods():
    too_few = pl.DataFrame({
        "_PERIOD_ID": [0, 1], "SCHEDULED_CASH_AMT": [1000.0, 1000.0],
        "DOLLAR_COLLECTION_RATE": [0.9, 0.95],
    })
    with pytest.raises(ValueError):
        bootstrap_cash_flow_at_risk(too_few, horizons_days=[30])


def test_bootstrap_cash_flow_at_risk_matches_hand_computed_closed_form():
    result = bootstrap_cash_flow_at_risk(
        _hand_built_periods(), horizons_days=[30, 60], period_days=30,
        n_anchor_periods=3, n_draws=20_000, seed=42,
    )
    assert result["real_rates_n"] == 5
    # Hand-computed: mean of the 3 most recent real SCHEDULED_CASH_AMT values
    # [1000, 2000, 3000] = 2000.0 exactly.
    assert result["near_term_scheduled_cash_per_period_assumption"] == pytest.approx(2000.0)

    h30 = result["by_horizon"][30]
    # Hand-computed closed-form: 2000.0 * 1 period * mean(rates)=0.90 = 1800.0
    assert h30["n_periods"] == 1
    assert h30["closed_form_mean"] == pytest.approx(2000.0 * 1 * 0.90)
    assert h30["mc_mean"] == pytest.approx(h30["closed_form_mean"], rel=0.02)
    assert h30["reconciles"] is True
    assert h30["p5_cfar"] <= h30["p50_expected"] <= h30["p95"]

    h60 = result["by_horizon"][60]
    # Hand-computed closed-form: 2000.0 * 2 periods * mean(rates)=0.90 = 3600.0
    assert h60["n_periods"] == 2
    assert h60["closed_form_mean"] == pytest.approx(2000.0 * 2 * 0.90)
    assert h60["reconciles"] is True


def test_bootstrap_cash_flow_at_risk_is_deterministic_given_same_seed():
    result_a = bootstrap_cash_flow_at_risk(_hand_built_periods(), horizons_days=[30], seed=42, n_draws=5_000)
    result_b = bootstrap_cash_flow_at_risk(_hand_built_periods(), horizons_days=[30], seed=42, n_draws=5_000)
    assert result_a["by_horizon"][30]["mc_mean"] == result_b["by_horizon"][30]["mc_mean"]
    assert result_a["by_horizon"][30]["p5_cfar"] == result_b["by_horizon"][30]["p5_cfar"]
