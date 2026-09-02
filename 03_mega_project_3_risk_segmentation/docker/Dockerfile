# Mega Project 3 — Risk Segmentation
# Deployable FastAPI scoring services (Problems 1, 2, 3, 4).
#
# BUILD CONTEXT: the SUITE ROOT (home-credit-enterprise-suite/), NOT this
# docker/ folder or 03_mega_project_3_risk_segmentation/ alone -- these
# services import the shared src/serving/ module that lives one level
# above this mega project, so the build needs both directories in one
# context. Build from the suite root:
#
#   cd home-credit-enterprise-suite
#   docker build -f 03_mega_project_3_risk_segmentation/docker/Dockerfile -t hc-mp3-services .
#
# PREREQUISITE (real, not optional): Notebooks 01-04 must have already been
# run at least once on YOUR machine before building this image --
# notebook_01_summary.json and notebook_0{2,3,4}_segment_model.joblib are
# real, user-generated artifacts, deliberately gitignored (never
# redistributed), so they exist locally only after you've run those notebooks.
FROM python:3.11-slim

WORKDIR /app

# Only the real dependencies these 4 services need at runtime (not the full
# notebook/EDA/reporting stack — this is a lean serving image, not the dev env).
COPY 03_mega_project_3_risk_segmentation/services/requirements-services.txt /app/requirements-services.txt
RUN pip install --no-cache-dir -r /app/requirements-services.txt

# Shared HYPER serving module + real fitted artifacts.
COPY src/serving /app/src/serving
COPY src/__init__.py /app/src/__init__.py
COPY 03_mega_project_3_risk_segmentation/services /app/services
COPY 03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_01_summary.json \
     /app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_01_summary.json
COPY 03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_02_segment_model.joblib \
     /app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_02_segment_model.joblib
COPY 03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_03_segment_model.joblib \
     /app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_03_segment_model.joblib
COPY 03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_04_segment_model.joblib \
     /app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_04_segment_model.joblib

ENV PYTHONPATH=/app/src
ENV NB01_SUMMARY_PATH=/app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_01_summary.json
ENV NB02_SEGMENT_MODEL_PATH=/app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_02_segment_model.joblib
ENV NB03_SEGMENT_MODEL_PATH=/app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_03_segment_model.joblib
ENV NB04_SEGMENT_MODEL_PATH=/app/03_mega_project_3_risk_segmentation/decision_engine/artifacts/notebook_04_segment_model.joblib

# Real, non-root runtime user (2026-09-02 hardening) -- these services never
# need root once dependencies are installed and files are copied in.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/services
EXPOSE 8007 8008 8009 8010

# Real liveness probe against each service's own unauthenticated /health
# endpoint (2026-09-02 hardening) -- the port is set per-service by
# docker-compose.yml's HEALTHCHECK_PORT env var below.
ENV HEALTHCHECK_PORT=8007
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"HEALTHCHECK_PORT\"]}/health', timeout=3)" || exit 1

# Default command runs Problem 1's service; docker-compose.yml overrides the
# command per real service/port for the other 3.
CMD ["uvicorn", "risk_tier_assignment_service:app", "--host", "0.0.0.0", "--port", "8007"]
