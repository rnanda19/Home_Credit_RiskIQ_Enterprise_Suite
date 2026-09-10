# Live Demo — Credit Default Prediction (Streamlit)

An interactive, click-and-try demo of Mega Project 1 Problem 1's real
trained champion model — the same model the suite's own
`credit_default_scoring_service.py` FastAPI service serves on `:8001` /
`:9001`. This app calls that service's exact same real scoring and
explainability functions (`src/serving/scoring_service_common.py`,
`src/serving/explainability_common.py`) directly — no separate demo-only
model, no fabricated numbers, no bundled Kaggle data.

**This folder ships the app, not a live URL.** Deploying it requires your
own free account on a hosting platform (Hugging Face Spaces below) —
that's a real account-creation and file-upload step only you can do, so
it isn't done automatically as part of building this repo.

## Why nothing is deployed yet

Two real, disclosed constraints, both intentional:

1. **The trained model bundle is `.gitignore`d, on purpose** (see
   `MODEL_REGISTRY.md`) — it's a real multi-megabyte artifact produced
   only by actually running `01_credit_default_prediction.ipynb` on your
   own real, locally-downloaded Home Credit data, and was never meant to
   live in this git repo. A live demo needs that real file *somewhere*
   the demo can read it — this repo alone can't provide that.
2. **Deploying to any hosting platform needs your own account.** Whether
   that's Hugging Face Spaces, Streamlit Community Cloud, or something
   else, only you can sign in and authorize it.

## Deploy to Hugging Face Spaces (recommended — free, no card required)

1. Go to <https://huggingface.co/new-space> and sign in (create a free
   account if you don't have one).
2. Space name: e.g. `home-credit-riskiq-demo`. SDK: **Streamlit**.
   Visibility: your choice (Public shows it to recruiters/reviewers).
3. Once the Space is created, open its **Files** tab and upload, from
   this repo:
   - `demo/streamlit_app.py` → rename to `app.py` at the Space root (or
     keep the path and set `app_file: demo/streamlit_app.py` in the
     Space's `README.md` frontmatter — either works)
   - `demo/requirements.txt` → `requirements.txt` at the Space root
   - `src/serving/scoring_service_common.py`,
     `src/serving/explainability_common.py`,
     `src/serving/adverse_action_common.py`,
     `src/serving/auth_common.py`,
     `src/serving/rate_limit_common.py`, `src/serving/__init__.py` →
     under a `src/serving/` folder in the Space (the demo imports these
     directly, same code as the real API — see the app's docstring)
4. Upload your own real, locally-produced
   `notebook_01_champion_model.joblib` (from
   `01_mega_project_1_underwriting_approval/decision_engine/artifacts/`
   on your own machine, after running Notebook 01) into the Space at
   `01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib`
   — matching this repo's real folder layout, so the app finds it at its
   default path with no extra configuration. (If you'd rather not upload
   the model file permanently, skip this step — the app's sidebar
   uploader lets any visitor supply it ad hoc for their own session.)
5. The Space builds automatically and gives you a live URL like
   `https://huggingface.co/spaces/<your-username>/home-credit-riskiq-demo`.
6. Paste that URL into `README.md`'s "Live Demo" section (top-level
   suite README) and into this file's badge line below, replacing the
   placeholder.

## Run it locally first (optional, to sanity-check before deploying)

```bash
pip install -r demo/requirements.txt
streamlit run demo/streamlit_app.py
```

Needs a real `notebook_01_champion_model.joblib` on disk at the default
path above (or use the in-app uploader) — produced by running Notebook 01
on your own real data, exactly like running the FastAPI service does.

## What the demo does and doesn't do

- **Does**: load the real bundle, run the exact same real preprocessing
  and `predict_proba()` call the deployed API uses, and compute a real,
  live, per-request explanation via the same occlusion method
  `/adverse-action-notice` uses (reset one real feature to baseline at a
  time, report the real resulting change in predicted probability).
- **Doesn't**: retrain anything, bundle or redistribute any real Kaggle
  data row, or show a result without a real model bundle loaded — with no
  bundle present, the app says so and stops rather than faking a score.
