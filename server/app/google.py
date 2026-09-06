"""Проверка Google ID-токена (только на сервере, спека §17).

Зеркало `app/apple.py`: клиент присылает ID-токен, полученный от Google, сервер
проверяет подпись по JWKS Google, сверяет издателя, аудиторию и срок, и связывает
аккаунт по устойчивому `sub`.

Почему не по почте: адрес у аккаунта Google меняется, а `sub` — нет. Почта здесь
берётся только для показа в профиле и только когда Google подтвердил её сам
(`email_verified`); входом она не управляет.

Google OAuth бесплатен: нужен один Client ID из Google Cloud Console, без биллинга.
Без него эндпоинт отвечает 503, а не делает вид, что что-то проверил.
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

# Google выдаёт токены то с одним, то с другим написанием издателя — исторически.
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleAuthError(RuntimeError):
    pass


class GoogleIdentity:
    """Кто вошёл: устойчивый идентификатор и — если Google её подтвердил — почта."""

    def __init__(self, subject: str, email: str | None):
        self.subject = subject
        self.email = email


def _load_jwks(force: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force and _JWKS_CACHE["keys"] and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]
    try:
        response = httpx.get(settings.google_jwks_url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network failure path
        raise GoogleAuthError("google_jwks_unavailable") from exc

    keys = {}
    for key in payload.get("keys", []):
        try:
            keys[key["kid"]] = RSAAlgorithm.from_jwk(key)
        except Exception:  # pragma: no cover - malformed key
            continue
    if not keys:
        raise GoogleAuthError("google_jwks_empty")
    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def verify_id_token(id_token: str) -> GoogleIdentity:
    """Возвращает личность из валидного ID-токена Google."""
    if not settings.google_client_id:
        raise GoogleAuthError("google_not_configured")

    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as exc:
        raise GoogleAuthError("google_token_malformed") from exc

    kid = header.get("kid")
    keys = _load_jwks()
    key = keys.get(kid)
    if key is None:
        # Google меняет ключи по расписанию: один промах — повод перечитать набор,
        # а не отказать человеку во входе.
        keys = _load_jwks(force=True)
        key = keys.get(kid)
    if key is None:
        raise GoogleAuthError("google_key_not_found")

    # Аудиторий может быть несколько: у веба и у мобильного клиента свои Client ID,
    # но аккаунт за ними один и тот же.
    audiences = [
        value
        for value in (settings.google_client_id, settings.google_ios_client_id)
        if value
    ]
    last_error: Exception | None = None
    for issuer in _ISSUERS:
        try:
            claims = jwt.decode(
                id_token, key=key, algorithms=["RS256"], audience=audiences, issuer=issuer
            )
            break
        except jwt.PyJWTError as exc:
            last_error = exc
    else:
        raise GoogleAuthError("google_token_invalid") from last_error

    subject = claims.get("sub")
    if not subject:
        raise GoogleAuthError("google_token_missing_sub")

    email = claims.get("email") if claims.get("email_verified") else None
    return GoogleIdentity(str(subject), email)
