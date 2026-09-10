#!/usr/bin/env bash
# Generates a real, local-only self-signed TLS certificate + key for one
# Mega Project's docker-compose.tls.yml. Shared across all 5 Mega Projects
# -- one script, not five near-identical copies.
#
# NEVER commit the generated cert.pem/key.pem (see .gitignore -- they are
# excluded by pattern). This is a REAL cert (same `openssl req -x509`
# mechanics as .github/workflows/docker-build-verify.yml's
# tls-termination-verify CI job), but self-signed and local-only -- a real
# production deployment behind an actual domain should replace these two
# files with a real CA-issued cert/key instead of running this script.
#
# Usage (from the suite root, or anywhere):
#   scripts/generate_local_tls_cert.sh 01_mega_project_1_underwriting_approval/docker/tls
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <mega_project_docker_tls_dir>" >&2
  echo "Example: $0 01_mega_project_1_underwriting_approval/docker/tls" >&2
  exit 1
fi

TARGET_DIR="$1"
mkdir -p "$TARGET_DIR"

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "$TARGET_DIR/key.pem" -out "$TARGET_DIR/cert.pem" -days 365 \
  -subj "/CN=localhost"

echo "Generated $TARGET_DIR/cert.pem and $TARGET_DIR/key.pem (local self-signed -- not for production)."
echo "Next: docker compose -f <mega_project>/docker/docker-compose.tls.yml up --build"
