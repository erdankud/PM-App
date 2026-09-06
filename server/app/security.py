"""Token issuing and verification.

Access tokens are short-lived JWTs signed with the server secret. Refresh tokens
are opaque random strings; only their SHA-256 hash is stored (spec §17).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RefreshToken, User, utcnow


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(user_id: str) -> tuple[str, int]:
    expires_in = settings.access_token_minutes * 60
    payload = {
        "sub": user_id,
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(seconds=expires_in)).timestamp()),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def issue_refresh_token(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=_now() + timedelta(days=settings.refresh_token_days),
    )
    db.add(record)
    return raw


def rotate_refresh_token(db: Session, raw: str) -> tuple[User, str] | None:
    record = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == hash_token(raw)).first()
    )
    if record is None or record.revoked_at is not None:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < _now():
        return None
    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None:
        return None
    record.revoked_at = utcnow()
    new_raw = issue_refresh_token(db, user)
    return user, new_raw


def revoke_all_refresh_tokens(db: Session, user_id: str) -> None:
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .update({RefreshToken.revoked_at: utcnow()}, synchronize_session=False)
    )


# --- Пароли ------------------------------------------------------------------
#
# scrypt из стандартной библиотеки, а не bcrypt или argon2: это полноценная
# функция вывода ключа с настраиваемой стоимостью, и она не добавляет в проект
# зависимость с нативной сборкой ради одной операции.
#
# Параметры — рекомендованные для интерактивного входа: n=2^15 занимает около
# 100 мс на процессор этого класса. Они лежат в самой строке хеша, поэтому их
# можно поднять, не ломая уже сохранённые пароли.

_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
# scrypt требует 128 * n * r * p байт, а OpenSSL по умолчанию не даёт больше 32 МиБ
# и отказывается ровно на этих параметрах. Предел задаём явно, с запасом.
_SCRYPT_MAXMEM = 128 * _SCRYPT_N * _SCRYPT_R * _SCRYPT_P * 2

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def hash_password(password: str) -> str:
    """`scrypt$n$r$p$соль$хеш`, всё в hex. Соль своя у каждого пароля."""
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Проверка постоянного времени. Отсутствие хеша — это `False`, а не исключение:
    у аккаунта, заведённого через Google, пароля нет, и вход по паролю в него
    невозможен ровно так же, как с неверным паролем."""
    if not stored:
        return False
    try:
        scheme, n, r, p, salt_hex, expected_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected_hex)),
            maxmem=128 * int(n) * int(r) * int(p) * 2,
        )
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(derived.hex(), expected_hex)


def normalise_email(email: str) -> str:
    """Регистр в адресе значения не имеет; пробелы по краям — почти всегда опечатка."""
    return email.strip().lower()
