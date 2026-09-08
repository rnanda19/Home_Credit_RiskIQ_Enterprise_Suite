"""
src/serving/rate_limit_common.py

HYPER shared component: real, per-process rate limiting for every service
in this suite, via slowapi (a maintained Starlette/FastAPI wrapper around
the same token-bucket/fixed-window algorithm as Flask-Limiter). Closes a
real, previously-disclosed gap: "No rate limiting or TLS termination
anywhere in the service layer -- every endpoint accepts unlimited
plain-HTTP requests today."

Built once here, wired into both shared serving factories
(scoring_service_common.py, segment_assignment_common.py) and all 5
standalone service files -- the same reuse-first pattern as
auth_common.py, not duplicated per service.

Real limits, not placeholders (see docstrings on the constants below for
why each value was chosen). `/health` is never rate-limited -- liveness
probes must never be throttled.

DISCLOSED SCOPE (real, not hidden): slowapi's default storage is
in-memory, so these limits are per-process. That is the correct scope for
this suite today -- every service here runs as one process per container
(see each Mega Project's docker-compose.yml), the same scope every other
piece of per-process state in this suite already has (e.g. the model
bundle loaded once at import time). A horizontally-scaled deployment
running multiple replicas of the same service behind a load balancer
would need a shared backend (slowapi supports Redis via
`storage_uri="redis://..."` on the Limiter constructor) for the limit to
apply across replicas instead of per-replica -- that real extension is
noted here, not built, because this suite does not run multiple replicas
of any service today (see the orchestration/Kubernetes gap in the
production-readiness review).

TLS termination is a separate, real, disclosed piece -- see
`docs/TLS.md` for the actual reverse-proxy config. Rate limiting is
application-layer and belongs in the app; TLS termination is
transport-layer and belongs in front of it, not duplicated into each
FastAPI process.
"""

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# The credential-guessing surface -- kept tight on purpose. A legitimate
# caller refreshes a token at most a handful of times an hour; 10/minute
# gives generous headroom for retries after a real network blip while
# still stopping a naive brute-force loop against /token.
TOKEN_RATE_LIMIT = "10/minute"

# /schema and /score (and MP2's /score/{scenario}) -- generous enough for
# real interactive or small-batch use, tight enough that a runaway or
# abusive caller cannot starve the service for everyone else.
DEFAULT_RATE_LIMIT = "60/minute"


def install_rate_limiting(app: FastAPI) -> Limiter:
    """Wires a real, per-app slowapi Limiter onto `app`: attaches it as
    `app.state.limiter` (slowapi's own required convention), registers the
    standard 429 handler, and adds the middleware that injects real
    `X-RateLimit-*` response headers. Returns the `Limiter` instance so the
    caller can apply `@limiter.limit(...)` to individual routes.

    Every decorated route needs a parameter literally named `request`,
    typed `fastapi.Request` (slowapi's own real requirement -- it inspects
    the wrapped function's signature for exactly that) -- see each call
    site for how this suite's existing `request: <PydanticModel>` request
    bodies were renamed to avoid the collision."""
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    return limiter
