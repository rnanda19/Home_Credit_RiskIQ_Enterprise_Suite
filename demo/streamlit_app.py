"""
Home Credit RiskIQ -- Live Credit Default Prediction Demo (Streamlit)

Interactive wrapper around Mega Project 1 Problem 1's real, already-trained
champion model bundle (notebook_01_champion_model.joblib) -- the same
"flagship" service the suite's docker-compose/TLS layer exposes on
:8001 / :9001 (credit_default_scoring_service.py).

This demo does NOT retrain or fabricate anything:
  - It imports and calls the exact same real, shared scoring functions the
    suite's own FastAPI service uses (src/serving/scoring_service_common.py
    -- load_bundle(), score_one() -- and src/serving/explainability_common.py
    -- top_reason_codes()), so a prediction made here is identical to what
    the deployed API would return for the same input. No separate demo-only
    scoring logic is written here (HYPER: reuse, don't duplicate).
  - No real Kaggle data rows are bundled with this app (the Home Credit
    Default Risk competition data is never redistributed -- see
    DATA_PRIVACY.md). Every field starts blank; a blank field is scored
    using the model's own real training-set baseline (the same "missing"
    convention the notebook and the API already use -- see
    scoring_service_common.py's docstring), never a fabricated default.
  - The real trained bundle itself is also never committed to git (see
    .gitignore / MODEL_REGISTRY.md) -- it's either uploaded once into this
    Streamlit Space's own persistent storage (see demo/README.md) or
    supplied ad hoc via the uploader below.

Run locally:
    streamlit run demo/streamlit_app.py
"""

import os
import sys
from pathlib import Path

import joblib
import streamlit as st

THIS_DIR = Path(__file__).resolve().parent
SUITE_ROOT = THIS_DIR.parent
sys.path.insert(0, str(SUITE_ROOT / "src"))

from serving.explainability_common import top_reason_codes  # noqa: E402
from serving.scoring_service_common import score_one  # noqa: E402

DEFAULT_BUNDLE_PATH = Path(
    os.environ.get(
        "NB01_BUNDLE_PATH",
        str(
            SUITE_ROOT
            / "01_mega_project_1_underwriting_approval"
            / "decision_engine"
            / "artifacts"
            / "notebook_01_champion_model.joblib"
        ),
    )
)

N_TOP_FEATURES = 15  # how many real features get their own input widget

st.set_page_config(
    page_title="Home Credit RiskIQ -- Live Demo",
    page_icon="\U0001f3e6",
    layout="wide",
)

st.title("Home Credit RiskIQ -- Live Credit Default Prediction Demo")
st.caption(
    "Mega Project 1, Problem 1 -- real trained champion model, real "
    "preprocessing, real per-request explanation. Nothing here is "
    "simulated: this is the exact scoring code the suite's own "
    "credit-default-prediction FastAPI service runs."
)


@st.cache_resource(show_spinner="Loading the real trained model bundle...")
def _load_bundle_from_path(path_str: str):
    path = Path(path_str)
    if not path.exists():
        return None
    bundle = joblib.load(path)
    bundle.setdefault("numeric_features", list(bundle["feature_cols"]))
    bundle.setdefault("categorical_features", [])
    bundle.setdefault("ordinal_encoder", None)
    return bundle


@st.cache_resource(show_spinner="Loading the uploaded model bundle...")
def _load_bundle_from_upload(file_bytes: bytes):
    import io

    bundle = joblib.load(io.BytesIO(file_bytes))
    bundle.setdefault("numeric_features", list(bundle["feature_cols"]))
    bundle.setdefault("categorical_features", [])
    bundle.setdefault("ordinal_encoder", None)
    return bundle


bundle = _load_bundle_from_path(str(DEFAULT_BUNDLE_PATH))

with st.sidebar:
    st.header("Model bundle")
    if bundle is not None:
        st.success(f"Loaded: `{DEFAULT_BUNDLE_PATH.name}`")
    else:
        st.warning(
            "No bundle found at the configured path yet. Upload your own "
            "real `notebook_01_champion_model.joblib` (produced by running "
            "01_credit_default_prediction.ipynb on your own real Home "
            "Credit data) to try the demo."
        )
        uploaded = st.file_uploader(
            "Upload notebook_01_champion_model.joblib", type=["joblib"]
        )
        if uploaded is not None:
            bundle = _load_bundle_from_upload(uploaded.getvalue())
            st.success("Uploaded bundle loaded.")

if bundle is None:
    st.info(
        "Waiting for a real trained model bundle (see the sidebar). This "
        "demo never fabricates a prediction -- without a real bundle it "
        "shows nothing rather than a fake score."
    )
    st.stop()

numeric_features = bundle["numeric_features"]
categorical_features = bundle["categorical_features"]
feature_cols = bundle["feature_cols"]
ord_enc = bundle["ordinal_encoder"]
champion_name = bundle.get("champion_name", "unknown")
model = bundle["model"]

st.sidebar.metric("Champion model", champion_name)
st.sidebar.metric("Total real features", len(feature_cols))

importances = getattr(model, "feature_importances_", None)
if importances is not None and len(importances) == len(feature_cols):
    ranked = [f for _, f in sorted(zip(importances, feature_cols), reverse=True)]
else:
    ranked = list(feature_cols)  # deterministic fallback, no fabricated ranking
top_features = ranked[:N_TOP_FEATURES]

st.subheader(f"Top {len(top_features)} most influential real features")
st.caption(
    "Every other real feature this model uses is left at the training "
    "set's own baseline (its real median/mode via the notebook's fitted "
    "imputer -- see scoring_service_common.py). Leave a field blank to "
    "keep that baseline; type a value to override it."
)

payload = {c: None for c in feature_cols}
cols = st.columns(3)
for i, feat in enumerate(top_features):
    with cols[i % 3]:
        if feat in categorical_features:
            options = ["(use baseline)"]
            if ord_enc is not None:
                try:
                    idx = list(categorical_features).index(feat)
                    options += [
                        str(c) for c in ord_enc.categories_[idx] if c != "Missing"
                    ]
                except Exception:
                    pass
            choice = st.selectbox(feat, options, key=f"in_{feat}")
            payload[feat] = None if choice == "(use baseline)" else choice
        else:
            val = st.number_input(feat, value=None, format="%.4f", key=f"in_{feat}")
            payload[feat] = val

st.divider()

if st.button("Score this applicant", type="primary"):
    proba = score_one(bundle, payload)
    baseline_payload = {f: None for f in numeric_features + categorical_features}
    top_reasons = top_reason_codes(
        predict_fn=lambda p: score_one(bundle, p),
        raw_payload=payload,
        baseline_payload=baseline_payload,
        n=5,
    )

    left, right = st.columns([1, 2])
    with left:
        st.metric("Real probability of default", f"{proba:.1%}")
        st.caption(f"Champion model: {champion_name}")
    with right:
        st.subheader("Real top reason codes")
        st.caption(
            "Exact marginal effect of resetting each real feature you set "
            "back to its baseline -- computed live against the loaded "
            "model, the same occlusion method the suite's own "
            "adverse-action-notice endpoint uses (see explainability_common.py)."
        )
        if top_reasons:
            st.table(
                [
                    {
                        "Factor": r["factor"],
                        "Effect on probability": f"{r['contribution']:+.1%}",
                    }
                    for r in top_reasons
                ]
            )
        else:
            st.write("Every field is at its baseline -- no deviation to explain yet.")

st.divider()
st.caption(
    "Source: [Home_Credit_RiskIQ_Enterprise_Suite](https://github.com/rnanda19/"
    "Home_Credit_RiskIQ_Enterprise_Suite). Built on the Kaggle "
    "[Home Credit Default Risk](https://www.kaggle.com/competitions/"
    "home-credit-default-risk) dataset -- raw data never redistributed."
)
