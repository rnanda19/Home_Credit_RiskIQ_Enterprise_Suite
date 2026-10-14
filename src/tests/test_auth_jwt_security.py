"""
src/tests/test_auth_jwt_security.py

Regression tests for the 2026-10-14 hardening pass: migrating
src/serving/auth_common.py's JWT backend from python-jose to PyJWT
(see that module's docstring and VALIDATION_REPORT.md for the full
rationale -- python-jose[cryptography]==3.5.0 carries CVE-2026-85394,
an algorithm-confusion vulnerability with no fixed release available
upstream).

These tests exist specifically to prove the four invalid-token classes
the CVE and the general JWT algorithm-confusion attack family cover are
all actually rejected by `require_auth`/`_decode_bearer_token`, not just
that the happy path still works (that is already covered by
src/tests/test_serving_common.py, which this file deliberately does not
duplicate):

  1. a syntactically invalid / tampered token            -> rejected
  2. an expired token                                     -> rejected
  3. algorithm confusion: a token re-signed with a
     *different* algorithm than the server allows
     (including the classic unsigned "alg: none" attack)  -> rejected
  4. unauthorized access: no credential at all, or a
     well-formed-but-wrong-scope token                    -> rejected

Every token below is crafted by hand with PyJWT/base64 directly (never
by calling `create_access_token`, which always produces a valid,
correctly-signed token) so each test is an independent, adversarial
check of `_decode_bearer_token`'s actual behavior -- not a tautology.
"""

import base64
import json
import sys
from pathlib import Path

import jwt as pyjwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

SUITE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SUITE_ROOT / "src"))

from serving.auth_common import (  # noqa: E402
    API_ACCESS_SCOPE,
    JWT_ALGORITHM,
    _decode_bearer_token,
    require_auth,
)

REAL_SECRET = "a-real-configured-jwt-secret-for-security-tests"


def _tiny_authenticated_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_auth)])
    def protected():
        return {"ok": True}

    return app


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# --------------------------------------------------------------------------
# 1. Invalid / tampered tokens
# --------------------------------------------------------------------------


def test_decode_rejects_a_structurally_invalid_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    assert _decode_bearer_token("this-is-not-a-jwt-at-all") is None


def test_decode_rejects_a_token_with_tampered_payload(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    token = pyjwt.encode({"sub": "x", "scopes": [API_ACCESS_SCOPE]}, REAL_SECRET, algorithm="HS256")
    header_b64, payload_b64, sig_b64 = token.split(".")
    # Flip the scopes claim without re-signing -- the signature now covers
    # different bytes than what's presented, so verification must fail.
    tampered_payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
    tampered_payload["scopes"] = ["admin:everything"]
    tampered_payload_b64 = _b64url(json.dumps(tampered_payload).encode())
    tampered_token = f"{header_b64}.{tampered_payload_b64}.{sig_b64}"
    assert _decode_bearer_token(tampered_token) is None


# --------------------------------------------------------------------------
# 2. Expired tokens
# --------------------------------------------------------------------------


def test_decode_rejects_an_expired_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    expired = pyjwt.encode(
        {"sub": "x", "scopes": [API_ACCESS_SCOPE], "iat": 0, "exp": 1},  # 1970 -- long expired
        REAL_SECRET,
        algorithm="HS256",
    )
    assert _decode_bearer_token(expired) is None


# --------------------------------------------------------------------------
# 3. Algorithm confusion (the CVE-2026-85394 attack family)
# --------------------------------------------------------------------------


def test_decode_rejects_a_token_signed_with_a_different_algorithm(monkeypatch):
    """The server only ever accepts JWT_ALGORITHM ("HS256"). A token that is
    otherwise well-formed and signed with the *same secret* but a
    *different* algorithm must still be rejected -- this is exactly what
    `algorithms=[JWT_ALGORITHM]` in _decode_bearer_token exists to stop,
    and is the general mitigation for algorithm-confusion attacks
    (including CVE-2026-85394's specific DER-key-as-HMAC-secret variant)."""
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    assert JWT_ALGORITHM == "HS256"
    other_alg_token = pyjwt.encode({"sub": "x", "scopes": [API_ACCESS_SCOPE]}, REAL_SECRET, algorithm="HS512")
    assert _decode_bearer_token(other_alg_token) is None


def test_decode_rejects_an_unsigned_alg_none_token(monkeypatch):
    """The classic JWT 'alg: none' forgery: an attacker crafts a token with
    no signature at all and hopes the verifier skips verification because
    the header says to. Hand-built (PyJWT refuses to encode "none" without
    an explicit opt-in that this codebase never takes), to prove the
    decode path rejects it regardless of how it was produced."""
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": "x", "scopes": [API_ACCESS_SCOPE]}).encode())
    none_alg_token = f"{header}.{payload}."
    assert _decode_bearer_token(none_alg_token) is None


def test_decode_rejects_a_token_forged_with_the_servers_own_public_surface(monkeypatch):
    """Even if an attacker somehow obtains a byte string the server treats
    as secret-shaped (the CVE's threat model: a DER-encoded public key
    used as an HMAC secret), signing with the *wrong* secret must still be
    rejected -- there is no code path here that accepts a differently-
    encoded form of the real secret."""
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    forged = pyjwt.encode(
        {"sub": "x", "scopes": [API_ACCESS_SCOPE]},
        base64.b64encode(REAL_SECRET.encode()).decode(),  # a differently-encoded, wrong secret
        algorithm="HS256",
    )
    assert _decode_bearer_token(forged) is None


# --------------------------------------------------------------------------
# 4. Unauthorized access
# --------------------------------------------------------------------------


def test_require_auth_rejects_no_credential_at_all(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    client = TestClient(_tiny_authenticated_app())
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_require_auth_rejects_a_well_formed_token_with_the_wrong_scope(monkeypatch):
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    wrong_scope_token = pyjwt.encode(
        {"sub": "x", "scopes": ["some:other:scope"]}, REAL_SECRET, algorithm="HS256"
    )
    client = TestClient(_tiny_authenticated_app())
    resp = client.get("/protected", headers={"Authorization": f"Bearer {wrong_scope_token}"})
    assert resp.status_code == 401


def test_require_auth_rejects_an_algorithm_confused_token_end_to_end(monkeypatch):
    """Same attack as test_decode_rejects_a_token_signed_with_a_different_algorithm,
    exercised through the real FastAPI dependency end-to-end rather than
    the decode helper directly."""
    monkeypatch.setenv("API_KEY", "a-real-configured-key")
    monkeypatch.setenv("JWT_SECRET_KEY", REAL_SECRET)
    other_alg_token = pyjwt.encode({"sub": "x", "scopes": [API_ACCESS_SCOPE]}, REAL_SECRET, algorithm="HS512")
    client = TestClient(_tiny_authenticated_app())
    resp = client.get("/protected", headers={"Authorization": f"Bearer {other_alg_token}"})
    assert resp.status_code == 401
