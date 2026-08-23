"""Authentication (spec §17).

Sign in with Apple is the production identity method. The dev path exists so the
client can be exercised before an Apple Developer account is configured; it is
disabled whenever ALLOW_DEV_AUTH is false and refused outright in production.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.apple import AppleAuthError, verify_identity_token
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import SKILL_KEYS, SkillScore, User, UserProfile, utcnow
from app.schemas import (
    AppleSignInRequest,
    AuthResponse,
    DevSignInRequest,
    RefreshRequest,
    SignOutRequest,
    SimpleOk,
)
from app.security import (
    create_access_token,
    issue_refresh_token,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
)
from app.services.path import resolve_timezone
from app.views import me_response

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_profile(db: DbSession, user: User) -> UserProfile:
    profile = db.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()
    existing = {
        row.skill_key
        for row in db.query(SkillScore).filter(SkillScore.user_id == user.id).all()
    }
    for key in SKILL_KEYS:
        if key not in existing:
            db.add(SkillScore(user_id=user.id, skill_key=key, score=50))
    return profile


def _issue(db: DbSession, user: User) -> AuthResponse:
    profile = _ensure_profile(db, user)
    access_token, expires_in = create_access_token(user.id)
    refresh = issue_refresh_token(db, user)
    db.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh,
        expires_in=expires_in,
        user=me_response(db, user, profile),
    )


def _apply_timezone(user: User, timezone_name: str | None) -> None:
    if timezone_name:
        user.timezone = str(resolve_timezone(timezone_name))


@router.post("/apple", response_model=AuthResponse)
def sign_in_with_apple(payload: AppleSignInRequest, db: DbSession) -> AuthResponse:
    if not settings.apple_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "apple_not_configured",
                "message": "Set APPLE_CLIENT_ID on the server to enable Sign in with Apple.",
            },
        )
    try:
        subject = verify_identity_token(payload.identity_token)
    except AppleAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": exc.args[0]}
        ) from exc

    # Account deletion clears the subject, so a deleted account signs back in as a
    # brand-new account with no history (spec §17).
    user = (
        db.query(User)
        .filter(User.apple_subject == subject, User.deleted_at.is_(None))
        .first()
    )
    if user is None:
        user = User(apple_subject=subject)
        db.add(user)
        db.flush()

    _apply_timezone(user, payload.timezone)
    user.last_active_at = utcnow()
    return _issue(db, user)


@router.post("/dev", response_model=AuthResponse)
def sign_in_dev(payload: DevSignInRequest, db: DbSession) -> AuthResponse:
    if not settings.allow_dev_auth or settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found"}
        )
    user = (
        db.query(User)
        .filter(User.dev_subject == payload.device_id, User.deleted_at.is_(None))
        .first()
    )
    if user is None:
        user = User(dev_subject=payload.device_id)
        db.add(user)
        db.flush()
    _apply_timezone(user, payload.timezone)
    user.last_active_at = utcnow()
    return _issue(db, user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> AuthResponse:
    rotated = rotate_refresh_token(db, payload.refresh_token)
    if rotated is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "refresh_token_invalid"},
        )
    user, new_refresh = rotated
    profile = _ensure_profile(db, user)
    access_token, expires_in = create_access_token(user.id)
    db.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=expires_in,
        user=me_response(db, user, profile),
    )


@router.post("/signout", response_model=SimpleOk)
def sign_out(payload: SignOutRequest, user: CurrentUser, db: DbSession) -> SimpleOk:
    revoke_all_refresh_tokens(db, user.id)
    db.commit()
    return SimpleOk()
