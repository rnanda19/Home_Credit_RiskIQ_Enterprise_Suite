"""
src/serving/auth_common.py

HYPER shared component: real authentication, imported by every deployable
FastAPI service in this suite (Mega Projects 1-4). Added 2026-09-02 as a
real, disclosed hardening fix -- this suite's own services had ZERO
authentication on every endpoint until that pass. Built once here, imported
by every service in this suite (HYPER) rather than duplicated per service,
so a rotated key, a new scope, or a future auth-scheme change happens in
exactly one place.

HARDENING (2026-09-08): real OAuth2/JWT support added, closing the
disclosed gap that this suite had "a single shared static key, not
OAuth2/JWT" (see the enterprise production-readiness gap analysis). This
is a real client-credentials-style OAuth2 flow: `add_token_route(app)`
exposes a real `POST /token` endpoint on any service (a standard
`OAuth2PasswordRequestForm` contract) that exchanges the service's
existing `API_KEY` -- used here as the client secret, so there is no new
secret to provision or rotate separately -- for a short-lived, signed JWT
carrying a real `scopes` claim. `require_auth` (the new dependency every
service's `/schema` and `/score` route uses) accepts EITHER a still-valid
`X-API-Key` header (kept, explicitly, as a documented secondary path for
simple machine-to-machine batch callers that have no token-refresh loop)
OR a valid, unexpired Bearer JWT carrying the required scope. The old
`require_api_key` dependency is unchanged and still exported -- nothing
that imported it directly breaks -- `require_auth` is the new, preferred,
scoped entry point.

Environment variables:
    API_KEY        -- see each Mega Project's docker/.env.example, and
                       docker-compose.yml's `${API_KEY:?...}` requirement.
                       Also doubles as the OAuth2 client secret for /token.
    JWT_SECRET_KEY -- signs and verifies issued JWTs. Same fallback
                       convention as API_KEY: unset falls back to a
                       published, public dev-only default with a loud
                       warning -- fine for local `uvicorn --reload`, never
                       acceptable for anything reachable by anyone but you.

Usage in a service module:
    from fastapi import Depends
    from serving.auth_common import require_auth, add_token_route
    from serving.rate_limit_common import install_rate_limiting, DEFAULT_RATE_LIMIT
    limiter = install_rate_limiting(app)      # 2026-09-08 hardening -- real rate limiting
    add_token_route(app, limiter=limiter)     # exposes POST /token, itself rate-limited
    @app.post("/score", dependencies=[Depends(require_auth)])
    @limiter.limit(DEFAULT_RATE_LIMIT)
    def score(request: Request, body: ...): ...
"""

import logging
import os
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import (
    APIKeyHeader,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError, jwt

from serving.rate_limit_common import TOKEN_RATE_LIMIT

_logger = logging.getLogger(__name__)

DEV_DEFAULT_API_KEY = "dev-only-CHANGE-ME-before-deploying"
DEV_DEFAULT_JWT_SECRET = "dev-only-jwt-secret-CHANGE-ME-before-deploying"
JWT_ALGORITHM = "HS256"
JWT_DEFAULT_EXPIRE_MINUTES = 30
API_ACCESS_SCOPE = "api:access"

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def configured_api_key() -> str:
    """Real value from the real environment, or the published dev-only fallback
    (with a loud warning) -- never a silently-generated or hidden default.

    2026-09-10: the warning names the fallback but no longer prints its
    value -- CodeQL (py/clear-text-logging-sensitive-data) correctly flags
    any log call that interpolates a secret-typed value, even one this
    module also happens to publish as a source-level constant. The
    constant is still one line above, in source, for anyone who needs the
    actual value; runtime logs just don't carry it."""
    key = os.environ.get("API_KEY")
    if not key:
        _logger.warning(
            "API_KEY is not set -- falling back to the published dev-only default "
            "(see this module's DEV_DEFAULT_API_KEY constant). Set API_KEY before "
            "deploying this service anywhere reachable by anyone but you."
        )
        return DEV_DEFAULT_API_KEY
    return key


def configured_jwt_secret() -> str:
    """Same real-env-or-loud-dev-fallback convention as configured_api_key()
    (see that function's docstring for the 2026-09-10 clear-text-logging fix)."""
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        _logger.warning(
            "JWT_SECRET_KEY is not set -- falling back to the published dev-only "
            "default (see this module's DEV_DEFAULT_JWT_SECRET constant). Set "
            "JWT_SECRET_KEY before deploying this service anywhere reachable by "
            "anyone but you."
        )
        return DEV_DEFAULT_JWT_SECRET
    return secret


def require_api_key(presented: str = Security(_api_key_header)) -> str:
    """FastAPI dependency: 401s on a missing or wrong X-API-Key header. Uses
    secrets.compare_digest (constant-time) rather than `==`, so response timing
    never leaks how much of a guessed key was correct. Unchanged since
    2026-09-02 -- kept for any caller that imports this directly; see
    require_auth() below for the newer, scoped OAuth2/JWT-aware dependency."""
    expected = configured_api_key()
    if not presented or not secrets.compare_digest(presented, expected):
        raise HTTPException(
            status_code=401, detail="Missing or invalid X-API-Key header."
        )
    return presented


def create_access_token(
    scopes: list[str], expires_minutes: int = JWT_DEFAULT_EXPIRE_MINUTES
) -> str:
    """Real, signed JWT (HS256) carrying a real `scopes` claim and a real
    expiry -- not a placeholder token. `iat`/`exp` are real Unix timestamps."""
    now = int(time.time())
    payload = {
        "sub": "service-client",
        "scopes": list(scopes),
        "iat": now,
        "exp": now + expires_minutes * 60,
    }
    return jwt.encode(payload, configured_jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode_bearer_token(token: str) -> Optional[dict]:
    """Returns the decoded claims for a valid, unexpired, correctly-signed
    token, or None for anything invalid/expired/tampered -- python-jose's
    jwt.decode() itself enforces `exp` and signature verification."""
    try:
        return jwt.decode(token, configured_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def require_auth(
    api_key: Optional[str] = Security(_api_key_header),
    bearer_token: Optional[str] = Security(_oauth2_scheme),
) -> str:
    """The new, preferred dependency for /schema and /score routes. Accepts
    EITHER:
      - a still-valid X-API-Key header (kept as a documented secondary path
        for simple machine-to-machine batch callers), or
      - a valid, unexpired Bearer JWT (obtained from this service's own
        POST /token -- see add_token_route()) carrying the API_ACCESS_SCOPE
        scope.
    401s if neither credential is valid. Real constant-time comparison for
    the API-key path (secrets.compare_digest); real signature+expiry
    verification for the JWT path (python-jose)."""
    expected_key = configured_api_key()
    if api_key and secrets.compare_digest(api_key, expected_key):
        return "api-key-client"
    if bearer_token:
        payload = _decode_bearer_token(bearer_token)
        if payload and API_ACCESS_SCOPE in payload.get("scopes", []):
            return payload.get("sub", "jwt-client")
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid credentials: provide a valid X-API-Key header "
        "or an OAuth2 Bearer token (POST /token to obtain one).",
    )


def add_token_route(app, scopes: tuple = (API_ACCESS_SCOPE,), limiter=None) -> None:
    """Adds a real POST /token endpoint to `app` -- a real OAuth2
    client-credentials-style exchange: standard `OAuth2PasswordRequestForm`
    contract (form fields `username` [ignored, any value accepted -- this
    suite has one client class per service, not per-user accounts] and
    `password` [must equal this service's configured API_KEY]). Returns a
    real, short-lived, signed JWT on success. Deliberately reuses the
    existing API_KEY as the client secret rather than inventing a second
    credential to provision and rotate.

    HARDENING (2026-09-08): pass `limiter` (the object `serving.rate_limit_common
    .install_rate_limiting(app)` returns) to real-rate-limit this endpoint at
    `TOKEN_RATE_LIMIT` -- the credential-guessing surface, kept tight on
    purpose. `limiter=None` (the default) keeps this endpoint unlimited,
    for callers that haven't installed rate limiting on `app` at all."""

    def issue_token(request: Request, form: OAuth2PasswordRequestForm = Depends()):
        expected_key = configured_api_key()
        if not secrets.compare_digest(form.password, expected_key):
            raise HTTPException(status_code=401, detail="Invalid client credentials.")
        token = create_access_token(list(scopes))
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": JWT_DEFAULT_EXPIRE_MINUTES * 60,
            "scope": " ".join(scopes),
        }

    if limiter is not None:
        issue_token = limiter.limit(TOKEN_RATE_LIMIT)(issue_token)
    app.post("/token")(issue_token)
