# TLS Termination

This document exists to close half of a real, previously-disclosed gap:
"No rate limiting or TLS termination anywhere in the service layer --
every endpoint accepts unlimited plain-HTTP requests today." Rate
limiting is closed by `src/serving/rate_limit_common.py` (see
`CHANGELOG.md`). This is the TLS half.

## What exists today, and how it was verified

TLS termination is transport-layer and belongs in front of each FastAPI
process, not duplicated into every service's own code -- so this suite's
services keep speaking plain HTTP internally (as they always have, and as
`docker-compose.yml` still runs them), and a real reverse proxy in front
of them terminates TLS.

**Verified end-to-end for one representative service** (MP1 Problem 1,
Credit Default Prediction -- this suite's flagship, most-reused model,
see `MODEL_REGISTRY.md`) in `.github/workflows/docker-build-verify.yml`'s
`tls-termination-verify` job, on every push to `main`:

1. A real self-signed certificate is generated fresh every run
   (`openssl req -x509 ...`) -- never a committed cert or key.
2. The real MP1 service is built and run exactly as
   `docker-build-verify`'s own job does.
3. A real nginx instance is installed on the runner and started as a real
   TLS-terminating reverse proxy (config:
   `01_mega_project_1_underwriting_approval/docker/tls/nginx.conf.example`),
   listening on `8443` and forwarding to the real running service on
   `127.0.0.1:8001`.
4. A real `curl -k https://127.0.0.1:8443/health` request is made through
   that TLS listener to the real running service, and the job fails if it
   doesn't succeed.

This is not a written-and-assumed config: the exact same mechanics (real
self-signed cert + real nginx + real FastAPI backend, real HTTPS request)
were run and verified locally before this job was written.

## Honest scope: what this covers today, and what it doesn't yet

**One representative service, not all 15.** Same honest shape as this
suite's other partial-but-real rollouts (see `MONITORING.md`'s identical
disclosure for drift monitoring). Extending this to another service is
mechanical: point `nginx.conf.example`'s `proxy_pass` at that service's
own port and re-run the same job pattern against its Dockerfile.

**Demonstrated in CI, not wired into `docker-compose.yml`.** The
`tls-termination-verify` job proves the mechanics work; it does not add
an nginx service to any Mega Project's `docker-compose.yml` for local or
production use. That's a real, separate next step -- a `docker-compose`
override file adding an `nginx` service (mounting a real cert/key you
generate yourself, e.g. via the same `openssl req -x509 ...` command
above, or a real CA-issued cert if you put a service behind an actual
domain) with `depends_on` the backend service and `ports: ["8443:8443"]`
published instead of the backend's own plain-HTTP port -- not yet built,
because it needs a real deployment target to be more than a config file
nobody runs.

**The demo backend port stays reachable directly.** In the CI job (and in
any equivalent local setup), the backend's plain-HTTP port (`8001`) is
still published/reachable unless something else blocks it. A real
deployment terminating TLS in front of a service should bind the
backend's port to `127.0.0.1` only (or put it on a Docker network the
reverse proxy alone can reach) so plain HTTP is not reachable from outside
at all -- disclosed here rather than silently assumed.

## Extending to more services

1. Copy `01_mega_project_1_underwriting_approval/docker/tls/nginx.conf.example`
   next to the target Mega Project's Dockerfile.
2. Change `proxy_pass http://127.0.0.1:8001;` to that service's own port.
3. Reuse the same three real steps from `tls-termination-verify`: generate
   a fresh self-signed cert, install nginx, `curl -k https://.../health`
   through it.
