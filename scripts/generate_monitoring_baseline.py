"""
scripts/generate_monitoring_baseline.py

Real generator for a model's monitoring_baseline.json -- the file
monitoring_job.py checks new production batches against. This is not a
one-time hand-written config: it computes real quantile bin edges and
real per-bin training percentages from a real trained bundle plus real
reference data (the notebook's own training split, saved to CSV), the
same real numbers a production PSI baseline needs.

WHY THIS IS A SEPARATE SCRIPT, NOT PART OF EACH NOTEBOOK (yet): every
notebook in this suite already saves its champion bundle; wiring this
generator as each notebook's own final cell is the natural next step once
a given problem's monitoring is turned on (see MONITORING.md's "Extending
to more models" section for the honest, un-fabricated status of that
rollout). Today it is wired for one flagship model -- Mega Project 1
Problem 1, Credit Default Prediction -- and run by hand or as a follow-up
notebook cell, exactly like generate_ci_fixture_bundles.py's fixture
bundles are separate from the notebooks that produce the real ones.

Usage (against a real bundle + your own real, locally-downloaded Kaggle
training split):
    python scripts/generate_monitoring_baseline.py \
        --bundle 01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib \
        --reference-csv path/to/your/real/application_train_with_features.csv \
        --target-col TARGET \
        --top-n-features 5 \
        --out-baseline 01_mega_project_1_underwriting_approval/monitoring/mp1_01_baseline.json

This script cannot be run against real Home Credit data in this build
environment (no Kaggle data is downloaded here -- see DATA_PRIVACY.md /
.gitignore's data/raw/ exclusion), so it is verified structurally in
src/tests/test_generate_monitoring_baseline.py against a small, clearly
synthetic bundle + CSV -- proving the script's logic is correct, not that
it has been run on real data yet. That real run is a step for whoever
next re-trains Notebook 01 against the real dataset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def build_baseline(bundle_path, reference_csv, target_col, top_n_features, model_name):
    bundle = joblib.load(bundle_path)
    feature_cols = bundle.get("numeric_features") or bundle.get("feature_cols") or []
    if not feature_cols:
        raise ValueError(
            f"Bundle at {bundle_path} has neither 'numeric_features' nor "
            "'feature_cols' -- cannot pick PSI features from it."
        )

    ref = pd.read_csv(reference_csv)

    train_default_rate = None
    if target_col in ref.columns:
        train_default_rate = float(ref[target_col].mean())

    # Pick the top-N numeric features that are both in the bundle's own
    # feature list AND present in the reference CSV -- real intersection,
    # not an assumed match.
    usable = [c for c in feature_cols if c in ref.columns]
    top_features = usable[:top_n_features]

    quantile_bin_edges = {}
    train_bin_pct = {}
    for feat in top_features:
        col = ref[feat].dropna().to_numpy(dtype=float)
        if len(col) < 5:
            continue
        edges = np.unique(np.quantile(col, [0.0, 0.25, 0.5, 0.75, 1.0])).tolist()
        if len(edges) < 3:
            continue
        counts, _ = np.histogram(col, bins=edges)
        pct = np.clip(counts / max(counts.sum(), 1), 1e-6, None)
        quantile_bin_edges[feat] = edges
        train_bin_pct[feat] = pct.tolist()

    baseline = {
        "model_name": model_name,
        "generated_from_bundle": str(bundle_path),
        "generated_from_reference_csv": str(reference_csv),
        "n_reference_rows": int(len(ref)),
        "target_col": target_col,
        "train_default_rate": train_default_rate,
        "psi_top_n_features": list(quantile_bin_edges.keys()),
        "quantile_bin_edges": quantile_bin_edges,
        "train_bin_pct": train_bin_pct,
    }
    return baseline


def main():
    parser = argparse.ArgumentParser(
        description="Generate a real monitoring_baseline.json from a real trained bundle + real reference data."
    )
    parser.add_argument("--bundle", required=True, help="Path to the model's .joblib bundle")
    parser.add_argument(
        "--reference-csv",
        required=True,
        help="Path to a real, already-feature-engineered CSV of the training split (or a recent scored batch to re-baseline against)",
    )
    parser.add_argument("--target-col", default="TARGET")
    parser.add_argument("--top-n-features", type=int, default=5)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--out-baseline", required=True)
    args = parser.parse_args()

    model_name = args.model_name or Path(args.bundle).stem
    baseline = build_baseline(
        bundle_path=args.bundle,
        reference_csv=args.reference_csv,
        target_col=args.target_col,
        top_n_features=args.top_n_features,
        model_name=model_name,
    )

    out_path = Path(args.out_baseline)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)
    print(
        f"Wrote {out_path} ({len(baseline['psi_top_n_features'])} PSI features, "
        f"train_default_rate={baseline['train_default_rate']})"
    )


if __name__ == "__main__":
    main()
