"""Sign in with Apple identity-token verification (server-side only, spec §17).

The client sends the identity token it received from ASAuthorization. The server
verifies the signature against Apple's JWKS, checks issuer/audience/expiry, and
links the account by the stable `sub` claim — never by email.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import settings

_JWKS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "keys": {}}
_JWKS_TTL_SECONDS = 3600


class AppleAuthError(RuntimeError):
    pass


def _load_jwks(force: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force and _JWKS_CACHE["keys"] and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]
    try:
        response = httpx.get(settings.apple_jwks_url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network failure path
        raise AppleAuthError("apple_jwks_unavailable") from exc

    keys = {}
    for key in payload.get("keys", []):
        try:
            keys[key["kid"]] = RSAAlgorithm.from_jwk(key)
        except Exception:  # pragma: no cover - malformed key
            continue
    if not keys:
        raise AppleAuthError("apple_jwks_empty")
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def verify_identity_token(identity_token: str) -> str:
    """Return the Apple `sub` for a valid identity token."""
    if not settings.apple_client_id:
        raise AppleAuthError("apple_not_configured")

    try:
        header = jwt.get_unverified_header(identity_token)
    except jwt.PyJWTError as exc:
        raise AppleAuthError("apple_token_malformed") from exc

    kid = header.get("kid")
    keys = _load_jwks()
    key = keys.get(kid)
    if key is None:
        keys = _load_jwks(force=True)
        key = keys.get(kid)
    if key is None:
        raise AppleAuthError("apple_key_not_found")

    try:
        claims = jwt.decode(
            identity_token,
            key=key,
            algorithms=["RS256"],
            audience=settings.apple_client_id,
            issuer=settings.apple_issuer,
        )
    except jwt.PyJWTError as exc:
        raise AppleAuthError("apple_token_invalid") from exc

    subject = claims.get("sub")
    if not subject:
        raise AppleAuthError("apple_token_missing_sub")
    return str(subject)
