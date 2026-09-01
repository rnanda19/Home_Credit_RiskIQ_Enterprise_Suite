"""
tests/test_stats_checks.py -- real pytest coverage for
src/utils/stats_checks.py's monotonic_within_noise(), the statistically-
principled monotonicity check introduced in CHANGELOG.md [1.0.2].

These are exact, independently-computed reference values (a manual
two-proportion z-test), not just "does it run" smoke tests -- consistent
with this suite's standing testing convention (see test_scoring_services.py).
"""
import math
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from utils.stats_checks import monotonic_within_noise  # noqa: E402


def _manual_two_proportion_p(p1, n1, p2, n2):
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z = (p2 - p1) / se
    return z, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def test_perfectly_monotonic_sequence_holds():
    rates = [0.10, 0.08, 0.06, 0.04, 0.02]
    counts = [10_000] * 5
    holds, detail = monotonic_within_noise(rates, counts)
    assert holds is True
    assert all(not row["reversed"] for row in detail)


def test_real_home_credit_case_from_user_report_is_not_significant():
    """The exact real-world case that motivated this fix: Notebook 04,
    Problem 4, on the real 307,499-applicant Home Credit population --
    'Weakest' (8.5122%, n=61,500) vs. 'Weak' (8.6992%, n=61,500), with the
    other 3 tiers monotonically decreasing beyond that. This reversal
    should NOT be flagged (z=1.17, p=0.24 -- not significant even at
    alpha=0.05 uncorrected, let alone Bonferroni-corrected)."""
    rates = [0.085122, 0.086992, 0.081268, 0.078309, 0.071969]
    counts = [61_500, 61_500, 61_500, 61_500, 61_499]
    holds, detail = monotonic_within_noise(rates, counts, alpha=0.05)
    assert holds is True
    reversed_pairs = [row for row in detail if row["reversed"]]
    assert len(reversed_pairs) == 1
    assert reversed_pairs[0]["pair_index"] == 0
    assert reversed_pairs[0]["statistically_significant_reversal"] is False
    assert 1.0 < reversed_pairs[0]["z"] < 1.3
    assert 0.20 < reversed_pairs[0]["p_value"] < 0.30
    # Cross-check against an independent manual computation of the same test.
    manual_z, manual_p = _manual_two_proportion_p(0.085122, 61_500, 0.086992, 61_500)
    assert math.isclose(reversed_pairs[0]["z"], manual_z, abs_tol=1e-6)
    assert math.isclose(reversed_pairs[0]["p_value"], manual_p, abs_tol=1e-6)


def test_large_real_reversal_is_flagged_significant():
    """A genuinely large, real reversal (not noise) must still fail --
    this check is a real statistical test, not a mechanism that always
    passes. 5% vs. 15% default rate at n=10,000 each is an enormous,
    unmistakable reversal."""
    rates = [0.30, 0.20, 0.05, 0.15, 0.02]
    counts = [10_000] * 5
    holds, detail = monotonic_within_noise(rates, counts)
    assert holds is False
    significant = [row for row in detail if row.get("statistically_significant_reversal")]
    assert len(significant) >= 1


def test_single_group_is_trivially_monotonic():
    holds, detail = monotonic_within_noise([0.10], [1000])
    assert holds is True
    assert detail == []


def test_bonferroni_correction_scales_with_number_of_pairs():
    """More adjacent pairs -> stricter (smaller) per-pair alpha. Verifies the
    correction is actually applied, not a fixed constant."""
    rates_2pair = [0.10, 0.105, 0.08]
    counts_2pair = [5000, 5000, 5000]
    _, detail_2 = monotonic_within_noise(rates_2pair, counts_2pair, alpha=0.05)
    reversed_2 = [r for r in detail_2 if r["reversed"]][0]
    assert abs(reversed_2["alpha_used_bonferroni_corrected"] - 0.025) < 1e-9

    rates_4pair = [0.10, 0.105, 0.09, 0.08, 0.06]
    counts_4pair = [5000] * 5
    _, detail_4 = monotonic_within_noise(rates_4pair, counts_4pair, alpha=0.05)
    reversed_4 = [r for r in detail_4 if r["reversed"]][0]
    assert abs(reversed_4["alpha_used_bonferroni_corrected"] - 0.0125) < 1e-9
