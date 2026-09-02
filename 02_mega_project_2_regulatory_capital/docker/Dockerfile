# Mega Project 2 — Regulatory Capital & Expected Loss
# Deployable FastAPI scoring services (Problems 1, 4).
#
# BUILD CONTEXT: the SUITE ROOT (home-credit-enterprise-suite/), NOT this
# docker/ folder or 02_mega_project_2_regulatory_capital/ alone -- these
# services import the shared src/features/ module that lives one level
# above this mega project, so the build needs both directories in one
# context. Build from the suite root:
#
#   cd home-credit-enterprise-suite
#   docker build -f 02_mega_project_2_regulatory_capital/docker/Dockerfile -t hc-mp2-services .
#
# NO model artifact prerequisite: unlike Mega Project 1's services, both of
# these are real, deterministic Basel/Vasicek FORMULA services -- neither
# loads a trained model, so nothing needs to be run first to build this image.
FROM python:3.11-slim

WORKDIR /app

# Only the real dependencies these 2 services need at runtime (not the full
# notebook/EDA/reporting stack — this is a lean serving image, not the dev env).
COPY 02_mega_project_2_regulatory_capital/services/requirements-services.txt /app/requirements-services.txt
RUN pip install --no-cache-dir -r /app/requirements-services.txt

# Shared HYPER feature module + this project's services.
COPY src/features/regulatory_capital_features.py /app/src/features/regulatory_capital_features.py
COPY src/features/__init__.py /app/src/features/__init__.py
COPY src/__init__.py /app/src/__init__.py
COPY 02_mega_project_2_regulatory_capital/services /app/services

ENV PYTHONPATH=/app/src

# Real, non-root runtime user (2026-09-02 hardening) -- these services never
# need root once dependencies are installed and files are copied in.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/services
EXPOSE 8005 8006

# Real liveness probe against each service's own unauthenticated /health
# endpoint (2026-09-02 hardening) -- the port is set per-service by
# docker-compose.yml's HEALTHCHECK_PORT env var below.
ENV HEALTHCHECK_PORT=8005
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"HEALTHCHECK_PORT\"]}/health', timeout=3)" || exit 1

# Default command runs Problem 1's service; docker-compose.yml overrides the
# command per real service/port for the other one.
CMD ["uvicorn", "capital_requirement_service:app", "--host", "0.0.0.0", "--port", "8005"]
