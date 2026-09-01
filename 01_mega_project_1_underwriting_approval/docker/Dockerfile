# Mega Project 1 — Intelligent Underwriting & Automated Credit Decisioning
# Deployable FastAPI scoring services (Problems 1, 2, 3, 4).
#
# BUILD CONTEXT: the SUITE ROOT (home-credit-enterprise-suite/), NOT this
# docker/ folder or 01_mega_project_1_underwriting_approval/ alone -- these
# services import the shared src/serving/ + src/utils/ modules that live one
# level above this mega project, so the build needs both directories in one
# context. Build from the suite root:
#
#   cd home-credit-enterprise-suite
#   docker build -f 01_mega_project_1_underwriting_approval/docker/Dockerfile -t hc-mp1-services .
#
# PREREQUISITE (real, not optional): Notebooks 01 and 02 must have already
# been run at least once on YOUR machine before building this image --
# notebook_01_champion_model.joblib / notebook_02_champion_model.joblib are
# real, user-generated model artifacts, deliberately gitignored (never
# redistributed), so they exist locally only after you've run those notebooks.
# The credit-score and repayment-capacity services need notebook_01's bundle
# only; notebooks 04/05 do not need a bundle at all.
FROM python:3.11-slim

WORKDIR /app

# Only the real dependencies these 4 services need at runtime (not the full
# notebook/EDA/reporting stack — this is a lean serving image, not the dev env).
COPY 01_mega_project_1_underwriting_approval/services/requirements-services.txt /app/requirements-services.txt
RUN pip install --no-cache-dir -r /app/requirements-services.txt

# Shared HYPER serving module + real trained model bundles.
COPY src/serving /app/src/serving
COPY src/__init__.py /app/src/__init__.py
COPY 01_mega_project_1_underwriting_approval/services /app/services
COPY 01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib \
     /app/01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib
COPY 01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_02_champion_model.joblib \
     /app/01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_02_champion_model.joblib

ENV PYTHONPATH=/app/src
ENV NB01_BUNDLE_PATH=/app/01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_01_champion_model.joblib
ENV NB02_BUNDLE_PATH=/app/01_mega_project_1_underwriting_approval/decision_engine/artifacts/notebook_02_champion_model.joblib

WORKDIR /app/services
EXPOSE 8001 8002 8003 8004

# Default command runs Problem 1's service; docker-compose.yml overrides the
# command per real service/port for the other 3.
CMD ["uvicorn", "credit_default_scoring_service:app", "--host", "0.0.0.0", "--port", "8001"]
