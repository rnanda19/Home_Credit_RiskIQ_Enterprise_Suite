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

**Verified end-to-end for all 15 deployable services across all 5 Mega
Projects** (extended 2026-09-10 from one representative service -- MP1
Problem 1 only) in `.github/workflows/docker-build-verify.yml`'s
`tls-termination-verify` job, on every push to `main`. One matrix entry
per Mega Project; each entry:

1. Builds that Mega Project's real Docker image once (same image every
   one of its services runs from, per `docker-compose.yml`'s pattern).
2. Starts every service in that Mega Project as its own real container,
   on its own real plain-HTTP port, waiting for each one's real `/health`
   to answer before continuing.
3. Generates a real self-signed certificate fresh every run
   (`openssl req -x509 ...`) -- never a committed cert or key.
4. Installs a real nginx instance on the runner and starts it as a real
   TLS-terminating reverse proxy, using that Mega Project's own real
   `docker/tls/nginx.conf` -- the exact same file `docker-compose.tls.yml`
   (below) bind-mounts for local/production use, not a separate
   CI-only variant.
5. Makes a real `curl -k https://127.0.0.1:<tls_port>/health` request
   through that TLS listener to every one of that Mega Project's real
   running services, and fails the job if any of them doesn't succeed.

This is not a written-and-assumed config: the exact same mechanics (real
self-signed cert + real nginx + real backends, real HTTPS requests) were
run and verified locally, for all 15 services at once, before this job
was extended -- a real nginx instance terminating TLS on 15 distinct real
ports, each reverse-proxying to a real backend under its real
docker-compose service name, every one reached over a real TLS 1.3
handshake.

**TLS port convention** (uniform across all 5 Mega Projects): TLS port =
`9000 +` the service's own plain-HTTP port's last 3 digits (`8001` ->
`9001`, ... `8015` -> `9015`). MP1 Problem 1's port changed from the
original demo's `8443` to `9001` as part of this extension, so every
service in the suite now follows one consistent, disclosed rule instead
of one service being a special case.

## Wired into `docker-compose.yml` for local/production use

Each Mega Project now has a real `docker/docker-compose.tls.yml` -- an
opt-in, standalone alternative to `docker-compose.yml` (which is
untouched and still runs exactly as before for plain-HTTP local dev).
`docker-compose.tls.yml` adds a real `nginx` service, terminating TLS in
front of every service in that Mega Project, and does **not** publish any
backend's plain-HTTP port externally -- each backend is reachable only
from nginx, over the internal Docker network, closing the "backend port
stays reachable directly" gap this document used to disclose.

Usage (from the suite root, per Mega Project):

```
scripts/generate_local_tls_cert.sh 01_mega_project_1_underwriting_approval/docker/tls
docker compose -f 01_mega_project_1_underwriting_approval/docker/docker-compose.tls.yml up --build
curl -k https://localhost:9001/health   # (and 9002/9003/9004 for this Mega Project's other services)
```

`scripts/generate_local_tls_cert.sh` is one shared script (not five
near-identical copies) that runs the same real `openssl req -x509`
command as the CI job, writing `cert.pem`/`key.pem` into the target
Mega Project's `docker/tls/` folder -- both gitignored, same reasoning as
`.env` (see `.gitignore`). For a real deployment behind an actual domain,
replace those two files with a real CA-issued cert/key instead of running
the script.

`API_KEY` is still required in `docker-compose.tls.yml` exactly as in
`docker-compose.yml` -- TLS termination protects the transport layer, it
does not replace authentication.

## Honest scope: what this covers today, and what it doesn't yet

- **All 15 services, both in CI and in the opt-in local/production
  compose files.** No longer a partial rollout -- same shape of
  disclosure this suite already gives for its other now-complete
  rollouts (E2E testing, adverse-action notices).
- **The `nginx` image itself is not pinned to a specific patch version
  beyond `1.27-alpine`** -- a real, disclosed choice for a portfolio
  project (favors a recent, small image) rather than a pinned digest a
  regulated production deployment would use.
- **Self-signed certs only, for local use.** Neither the CI job nor
  `docker-compose.tls.yml` obtains a real CA-issued certificate (e.g. via
  ACME/Let's Encrypt) -- that requires a real domain and a real deployment
  target to be more than a config file nobody runs, and stays a disclosed,
  open item.
- **No automatic cert renewal.** The generated self-signed cert is valid
  for 365 days (`generate_local_tls_cert.sh`) or 1 day (the CI job's fresh
  one each run) -- there is no renewal job, because there is no long-lived
  real deployment yet for one to run against.

## Extending further / rotating the port convention

1. Add or rename a service in a Mega Project's `docker-compose.yml`?
   Add the matching backend block (no `ports:`) to that Mega Project's
   `docker-compose.tls.yml`, add a `server` block to its
   `docker/tls/nginx.conf` on `9000 + <its plain-HTTP port>`, and add it
   to `docker-build-verify.yml`'s `tls-termination-verify` matrix entry's
   `services_json` for that Mega Project.
2. All three files (`docker-compose.tls.yml`, `docker/tls/nginx.conf`,
   the CI matrix entry) are generated from the same service list per
   Mega Project -- keep them in sync by construction, not by hand-editing
   three places independently.
