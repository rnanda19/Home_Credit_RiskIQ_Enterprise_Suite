# Mega Project 5 — Liquidity & Cashflow
# Deployable FastAPI scoring service (Problem 4 -- the only one of this
# Mega Project's 5 problems with a per-applicant service; Problems 1, 2,
# 3, and 5 are portfolio/macro-level and have none by design).
#
# BUILD CONTEXT: the SUITE ROOT (home-credit-enterprise-suite/), NOT this
# docker/ folder or 05_mega_project_5_liquidity_cashflow/ alone -- this
# service imports the shared src/serving/ module that lives one level
# above this mega project, so the build needs both directories in one
# context. Build from the suite root:
#
#   cd home-credit-enterprise-suite
#   docker build -f 05_mega_project_5_liquidity_cashflow/docker/Dockerfile -t hc-mp5-services .
#
# PREREQUISITE (real, not optional): Notebook 04 must have already been run
# at least once on YOUR machine before building this image --
# notebook_04_segment_model.joblib is a real, user-generated artifact,
# deliberately gitignored (never redistributed), so it exists locally only
# after you've run that notebook. As of this Dockerfile being added
# (2026-09-02), that rerun has not yet happened — see the Problem 4 model
# card for the current status; this image will build but the service will
# fail fast at startup until the bundle exists.
#
# Built hardened from day one: real X-API-Key auth on /schema and /score
# (see src/serving/auth_common.py, reused unchanged from Mega Projects
# 1/3/4), a non-root runtime user, and a real HEALTHCHECK.
FROM python:3.11-slim

WORKDIR /app

# Only the real dependency this 1 service needs at runtime (not the full
# notebook/EDA/reporting stack — this is a lean serving image, not the dev env).
COPY 05_mega_project_5_liquidity_cashflow/services/requirements-services.txt /app/requirements-services.txt
RUN pip install --no-cache-dir -r /app/requirements-services.txt

# Shared HYPER serving module + real trained model bundle.
COPY src/serving /app/src/serving
COPY src/__init__.py /app/src/__init__.py
COPY 05_mega_project_5_liquidity_cashflow/services /app/services
COPY 05_mega_project_5_liquidity_cashflow/decision_engine/artifacts/notebook_04_segment_model.joblib \
     /app/05_mega_project_5_liquidity_cashflow/decision_engine/artifacts/notebook_04_segment_model.joblib

ENV PYTHONPATH=/app/src
ENV NB04_SEGMENT_MODEL_PATH=/app/05_mega_project_5_liquidity_cashflow/decision_engine/artifacts/notebook_04_segment_model.joblib

# Real, non-root runtime user -- this service never needs root once
# dependencies are installed and files are copied in.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/services
EXPOSE 8015

# Real liveness probe against this service's own unauthenticated /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8015/health', timeout=3)" || exit 1

CMD ["uvicorn", "prepayment_segment_assignment_service:app", "--host", "0.0.0.0", "--port", "8015"]
