# Mega Project 4 — Delinquency Prevention
# Deployable FastAPI scoring services (Problems 1, 2, 3, 4).
#
# BUILD CONTEXT: the SUITE ROOT (home-credit-enterprise-suite/), NOT this
# docker/ folder or 04_mega_project_4_delinquency_prevention/ alone -- these
# services import the shared src/serving/ module that lives one level
# above this mega project, so the build needs both directories in one
# context. Build from the suite root:
#
#   cd home-credit-enterprise-suite
#   docker build -f 04_mega_project_4_delinquency_prevention/docker/Dockerfile -t hc-mp4-services .
#
# PREREQUISITE (real, not optional): Notebooks 01-04 must have already been
# run at least once on YOUR machine before building this image --
# notebook_01/03/04_champion_model.joblib and notebook_02_kmeans_model.joblib
# are real, user-generated artifacts, deliberately gitignored (never
# redistributed), so they exist locally only after you've run those notebooks.
#
# Built hardened from day one (2026-09-02): real X-API-Key auth on every
# /schema and /score endpoint (see src/serving/auth_common.py), a non-root
# runtime user, and a real HEALTHCHECK -- see CHANGELOG.md [1.9.7]/[1.9.8]
# for why (this suite's own 10 pre-existing services needed a retrofit for
# this same gap; Mega Project 4 never had it in the first place).
FROM python:3.11-slim

WORKDIR /app

# Only the real dependencies these 4 services need at runtime (not the full
# notebook/EDA/reporting stack — this is a lean serving image, not the dev env).
COPY 04_mega_project_4_delinquency_prevention/services/requirements-services.txt /app/requirements-services.txt
RUN pip install --no-cache-dir -r /app/requirements-services.txt

# Shared HYPER serving module + real trained model bundles.
COPY src/serving /app/src/serving
COPY src/__init__.py /app/src/__init__.py
COPY 04_mega_project_4_delinquency_prevention/services /app/services
COPY 04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_01_champion_model.joblib \
     /app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_01_champion_model.joblib
COPY 04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_02_kmeans_model.joblib \
     /app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_02_kmeans_model.joblib
COPY 04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_03_champion_model.joblib \
     /app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_03_champion_model.joblib
COPY 04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_04_champion_model.joblib \
     /app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_04_champion_model.joblib

ENV PYTHONPATH=/app/src
ENV NB01_BUNDLE_PATH=/app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_01_champion_model.joblib
ENV NB02_KMEANS_MODEL_PATH=/app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_02_kmeans_model.joblib
ENV NB03_BUNDLE_PATH=/app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_03_champion_model.joblib
ENV NB04_BUNDLE_PATH=/app/04_mega_project_4_delinquency_prevention/decision_engine/artifacts/notebook_04_champion_model.joblib

# Real, non-root runtime user -- these services never need root once
# dependencies are installed and files are copied in.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/services
EXPOSE 8011 8012 8013 8014

# Real liveness probe against each service's own unauthenticated /health
# endpoint -- the port is set per-service by docker-compose.yml's
# HEALTHCHECK_PORT env var below.
ENV HEALTHCHECK_PORT=8011
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"HEALTHCHECK_PORT\"]}/health', timeout=3)" || exit 1

# Default command runs Problem 1's service; docker-compose.yml overrides the
# command per real service/port for the other 3.
CMD ["uvicorn", "early_delinquency_scoring_service:app", "--host", "0.0.0.0", "--port", "8011"]
