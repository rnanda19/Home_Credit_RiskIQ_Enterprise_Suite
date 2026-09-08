"""Structural verification for generate_monitoring_baseline.py against a
small, clearly synthetic bundle + reference CSV (this build environment
has no real, locally-downloaded Kaggle data to run it against -- see the
script's own docstring). Proves the generator's logic is correct: real
quantile edges, real per-bin training percentages, and a real default
rate computed from whatever is actually in the reference CSV -- not that
it has been run against real data yet.
"""

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_monitoring_baseline import build_baseline  # noqa: E402


@pytest.fixture
def synthetic_bundle_and_reference(tmp_path):
    rng = np.random.default_rng(42)
    n = 200
    ref = pd.DataFrame(
        {
            "ci_fixture_feature_1": rng.normal(size=n),
            "ci_fixture_feature_2": rng.uniform(size=n),
            "TARGET": rng.integers(0, 2, size=n),
        }
    )
    ref_path = tmp_path / "reference.csv"
    ref.to_csv(ref_path, index=False)

    bundle = {
        "feature_cols": ["ci_fixture_feature_1", "ci_fixture_feature_2"],
        "numeric_features": ["ci_fixture_feature_1", "ci_fixture_feature_2"],
    }
    bundle_path = tmp_path / "fixture_bundle.joblib"
    joblib.dump(bundle, bundle_path)
    return bundle_path, ref_path, ref


def test_build_baseline_computes_real_default_rate_from_reference_csv(
    synthetic_bundle_and_reference,
):
    bundle_path, ref_path, ref = synthetic_bundle_and_reference
    baseline = build_baseline(
        bundle_path=bundle_path,
        reference_csv=ref_path,
        target_col="TARGET",
        top_n_features=5,
        model_name="fixture-model",
    )
    assert baseline["train_default_rate"] == pytest.approx(ref["TARGET"].mean())
    assert baseline["n_reference_rows"] == len(ref)


def test_build_baseline_only_uses_features_present_in_both_bundle_and_reference(
    synthetic_bundle_and_reference,
):
    bundle_path, ref_path, _ref = synthetic_bundle_and_reference
    baseline = build_baseline(
        bundle_path=bundle_path,
        reference_csv=ref_path,
        target_col="TARGET",
        top_n_features=5,
        model_name="fixture-model",
    )
    assert set(baseline["psi_top_n_features"]) == {
        "ci_fixture_feature_1",
        "ci_fixture_feature_2",
    }


def test_build_baseline_quantile_edges_and_train_bin_pct_are_real_and_consistent(
    synthetic_bundle_and_reference,
):
    bundle_path, ref_path, ref = synthetic_bundle_and_reference
    baseline = build_baseline(
        bundle_path=bundle_path,
        reference_csv=ref_path,
        target_col="TARGET",
        top_n_features=5,
        model_name="fixture-model",
    )
    for feat in baseline["psi_top_n_features"]:
        edges = baseline["quantile_bin_edges"][feat]
        pct = baseline["train_bin_pct"][feat]
        assert len(pct) == len(edges) - 1
        assert sum(pct) == pytest.approx(1.0, abs=1e-3)
        # The edges really are this feature's own real quantiles.
        assert edges[0] == pytest.approx(ref[feat].min())
        assert edges[-1] == pytest.approx(ref[feat].max())


def test_build_baseline_respects_top_n_features_cap(synthetic_bundle_and_reference):
    bundle_path, ref_path, _ref = synthetic_bundle_and_reference
    baseline = build_baseline(
        bundle_path=bundle_path,
        reference_csv=ref_path,
        target_col="TARGET",
        top_n_features=1,
        model_name="fixture-model",
    )
    assert len(baseline["psi_top_n_features"]) == 1


def test_build_baseline_raises_when_bundle_has_no_feature_list(tmp_path):
    bundle_path = tmp_path / "empty_bundle.joblib"
    joblib.dump({"model": "not-a-real-model"}, bundle_path)
    ref_path = tmp_path / "reference.csv"
    pd.DataFrame({"TARGET": [0, 1, 0, 1]}).to_csv(ref_path, index=False)

    with pytest.raises(ValueError):
        build_baseline(
            bundle_path=bundle_path,
            reference_csv=ref_path,
            target_col="TARGET",
            top_n_features=5,
            model_name="fixture-model",
        )
