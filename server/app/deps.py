"""Shared FastAPI dependencies: DB session and ownership-enforcing auth."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, utcnow
from app.security import decode_access_token

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code},
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized("missing_bearer_token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("token_expired") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("token_invalid") from exc

    if payload.get("typ") != "access":
        raise _unauthorized("token_invalid")

    user = db.get(User, payload.get("sub"))
    if user is None or user.deleted_at is not None:
        raise _unauthorized("account_not_found")

    user.last_active_at = utcnow()
    db.commit()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str | None:
    if idempotency_key is not None and len(idempotency_key) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "idempotency_key_too_long"},
        )
    return idempotency_key


IdempotencyKey = Annotated[str | None, Depends(idempotency_key)]
