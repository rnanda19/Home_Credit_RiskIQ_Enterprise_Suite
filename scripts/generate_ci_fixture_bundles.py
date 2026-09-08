#!/usr/bin/env python3
"""
scripts/generate_ci_fixture_bundles.py

Generates SYNTHETIC, clearly-fake model bundles at the exact paths each Mega
Project's Dockerfile expects to COPY, so `docker build` can succeed in CI
without a real trained model on disk. Real model artifacts are `.gitignore`d
by design (see MODEL_REGISTRY.md) and are only ever produced by actually
running a notebook against the real, locally-downloaded Kaggle dataset --
which CI does not do and is not meant to do here.

THIS IS A BUILD/RUN VERIFICATION FIXTURE ONLY. It proves:
  - the Dockerfile's COPY paths, dependencies, and startup command are
    correct (the image builds),
  - the FastAPI service actually starts and serves /health inside the
    container (the image runs).

It proves NOTHING about model quality, accuracy, or correctness -- the
"model" here is fit on 4 rows of made-up numbers. Real model validation
happens entirely at the notebook level, on the real dataset, and is
reported in each problem's own MODEL_CARD.md.

Used by .github/workflows/docker-build-verify.yml. Safe to run locally too
(e.g. to smoke-test a Dockerfile change without waiting for CI), but never
commit its output -- every path here is already `.gitignore`d.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

SUITE_ROOT = Path(__file__).resolve().parent.parent

# A tiny, genuinely-fit (not mocked) scikit-learn model -- real object,
# fake data. Fit once, reused for every scoring-bundle fixture below.
_X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 1.0], [2.0, 5.0]])
_y = np.array([0, 1, 0, 1])
_imputer = SimpleImputer(strategy="median").fit(_X)
_model = LogisticRegression().fit(_imputer.transform(_X), _y)


def scoring_bundle() -> dict:
    """MP1/MP4 classifier-service shape (all-numeric variant -- see
    src/serving/scoring_service_common.py's module docstring)."""
    return {
        "model": _model,
        "imputer": _imputer,
        "feature_cols": ["ci_fixture_feature_1", "ci_fixture_feature_2"],
        "champion_name": "LogisticRegression (CI fixture -- not a real trained model)",
    }


def segment_bundle() -> dict:
    """MP3/MP4 clustering-service shape (canonical key names -- see
    src/serving/segment_assignment_common.py's module docstring; the
    module's own setdefault() fallback makes this compatible with both
    MP3's and MP4-02's real bundle shapes)."""
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 1.0], [2.0, 5.0]])
    scaler = StandardScaler().fit(X)
    kmeans = KMeans(n_clusters=2, n_init=10, random_state=42).fit(scaler.transform(X))
    return {
        "kmeans": kmeans,
        "scaler": scaler,
        "feature_names": ["ci_fixture_feature_1", "ci_fixture_feature_2"],
        "segment_labels": ["Fixture Segment A", "Fixture Segment B"],
        "k_chosen": 2,
        "random_seed": 42,
    }


def write_bundle(path: Path, bundle: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    print(f"[fixture] wrote {path}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f)
    print(f"[fixture] wrote {path}")


def main() -> None:
    mp1 = SUITE_ROOT / "01_mega_project_1_underwriting_approval" / "decision_engine" / "artifacts"
    write_bundle(mp1 / "notebook_01_champion_model.joblib", scoring_bundle())
    write_bundle(mp1 / "notebook_02_champion_model.joblib", scoring_bundle())

    mp3 = SUITE_ROOT / "03_mega_project_3_risk_segmentation" / "decision_engine" / "artifacts"
    write_json(
        mp3 / "notebook_01_summary.json",
        {"tiering_config": {"tier_bin_edges": [None, 0.3, 0.6, None]}},
    )
    write_bundle(mp3 / "notebook_02_segment_model.joblib", segment_bundle())
    write_bundle(mp3 / "notebook_03_segment_model.joblib", segment_bundle())
    write_bundle(mp3 / "notebook_04_segment_model.joblib", segment_bundle())

    mp4 = SUITE_ROOT / "04_mega_project_4_delinquency_prevention" / "decision_engine" / "artifacts"
    write_bundle(mp4 / "notebook_01_champion_model.joblib", scoring_bundle())
    write_bundle(mp4 / "notebook_02_kmeans_model.joblib", segment_bundle())
    write_bundle(mp4 / "notebook_03_champion_model.joblib", scoring_bundle())
    write_bundle(mp4 / "notebook_04_champion_model.joblib", scoring_bundle())

    mp5 = SUITE_ROOT / "05_mega_project_5_liquidity_cashflow" / "decision_engine" / "artifacts"
    write_bundle(mp5 / "notebook_04_segment_model.joblib", segment_bundle())

    # Mega Project 2's services (capital_requirement_service, stress_testing_service)
    # are pure closed-form Basel formula services -- no model bundle needed at all.
    print("[fixture] Mega Project 2 needs no bundle (formula-only services) -- skipped.")


if __name__ == "__main__":
    main()
