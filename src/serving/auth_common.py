"""
src/serving/auth_common.py

HYPER shared component: real API-key authentication, imported by every
deployable FastAPI service in this suite (Mega Projects 1-4). Added
2026-09-02 as a real, disclosed hardening fix -- this suite's own services
had ZERO authentication on every endpoint until this pass. This is the same
class of gap identified and fixed in the AMEX RiskIQ Enterprise Credit Risk
Platform's own hardening history (a related project on this account) --
that platform's own main.py documents it as "the single largest gap ... no
service had any authentication." Built once here, imported by every service
in this suite (HYPER) rather than duplicated per service, so a rotated key
or a future auth-scheme change happens in exactly one place.

Environment variable: API_KEY (see each Mega Project's docker/.env.example,
and docker-compose.yml's `${API_KEY:?...}` requirement -- never baked into
a Docker image layer). If API_KEY is unset, falls back to a published,
public dev-only default with a loud warning -- fine for a local
`uvicorn --reload` session, never acceptable for anything reachable by
anyone but you.

Usage in a service module:
    from fastapi import Depends
    from serving.auth_common import require_api_key
    @app.post("/score", dependencies=[Depends(require_api_key)])
    def score(...): ...
"""
import logging
import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_logger = logging.getLogger(__name__)

DEV_DEFAULT_API_KEY = "dev-only-CHANGE-ME-before-deploying"

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def configured_api_key() -> str:
    """Real value from the real environment, or the published dev-only fallback
    (with a loud warning) -- never a silently-generated or hidden default."""
    key = os.environ.get("API_KEY")
    if not key:
        _logger.warning(
            "API_KEY is not set -- falling back to the published dev-only default "
            "(%s). Set API_KEY before deploying this service anywhere reachable by "
            "anyone but you.", DEV_DEFAULT_API_KEY,
        )
        return DEV_DEFAULT_API_KEY
    return key


def require_api_key(presented: str = Security(_api_key_header)) -> str:
    """FastAPI dependency: 401s on a missing or wrong X-API-Key header. Uses
    secrets.compare_digest (constant-time) rather than `==`, so response timing
    never leaks how much of a guessed key was correct."""
    expected = configured_api_key()
    if not presented or not secrets.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")
    return presented
