"""Вход: почта с паролем, Google и то, что сервер о них рассказывает.

Проверяется не «работает ли счастливый путь», а границы: чужой пароль не пускает,
занятый адрес отвечает своим кодом, аккаунт без пароля не открывается пустой
строкой, а список способов не обещает того, чего сервер не умеет.
"""

from __future__ import annotations

import uuid

from app.config import settings
from app.security import hash_password, normalise_email, verify_password


def credentials(password: str = "correct horse battery") -> dict:
    return {"email": f"{uuid.uuid4().hex}@example.com", "password": password}


# --- Хеш пароля ---------------------------------------------------------------


def test_the_same_password_hashes_differently_every_time():
    """Своя соль у каждого пароля: одинаковые пароли не видно по одинаковым хешам."""
    first, second = hash_password("hunter2hunter2"), hash_password("hunter2hunter2")
    assert first != second
    assert verify_password("hunter2hunter2", first)
    assert verify_password("hunter2hunter2", second)


def test_a_wrong_password_and_an_absent_hash_both_fail():
    stored = hash_password("hunter2hunter2")
    assert not verify_password("hunter2hunter3", stored)
    assert not verify_password("", stored)
    # У аккаунта из Google пароля нет — войти в него по паролю нельзя.
    assert not verify_password("anything", None)
    assert not verify_password("anything", "")


def test_the_address_is_matched_without_case_or_spaces():
    assert normalise_email("  Erdan@Example.COM ") == "erdan@example.com"


# --- Регистрация и вход --------------------------------------------------------


def test_signup_creates_an_account_and_signs_it_in(client):
    payload = credentials()
    response = client.post("/v1/auth/signup", json=payload)

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["accessToken"] and body["refreshToken"]
    # Онбординг ещё не пройден: регистрация — это не «всё готово».
    assert body["user"]["onboardingStatus"] == "signed_in"

    headers = {"Authorization": f"Bearer {body['accessToken']}"}
    assert client.get("/v1/me", headers=headers).status_code == 200


def test_the_same_address_cannot_be_taken_twice(client):
    payload = credentials()
    assert client.post("/v1/auth/signup", json=payload).status_code == 201

    again = client.post("/v1/auth/signup", json=payload)
    assert again.status_code == 409
    # Свой код, а не «неверные данные»: человеку надо сказать «войдите».
    assert again.json()["detail"]["code"] == "email_taken"


def test_signin_accepts_the_password_and_refuses_anything_else(client):
    payload = credentials()
    client.post("/v1/auth/signup", json=payload)

    ok = client.post("/v1/auth/signin", json=payload)
    assert ok.status_code == 200

    wrong = client.post(
        "/v1/auth/signin", json={**payload, "password": "not the password"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"]["code"] == "invalid_credentials"

    unknown = client.post("/v1/auth/signin", json=credentials())
    assert unknown.status_code == 401
    # Тот же код, что и у неверного пароля: по ответу нельзя перебрать адреса.
    assert unknown.json()["detail"]["code"] == "invalid_credentials"


def test_the_address_is_case_insensitive_at_sign_in(client):
    payload = credentials()
    client.post("/v1/auth/signup", json=payload)
    upper = {**payload, "email": payload["email"].upper()}
    assert client.post("/v1/auth/signin", json=upper).status_code == 200


def test_a_short_password_is_refused_before_it_is_stored(client):
    short = client.post("/v1/auth/signup", json=credentials("short"))
    assert short.status_code == 422


def test_a_signed_up_account_keeps_its_progress_across_sessions(client):
    """Аккаунт — это прогресс: второй вход должен вернуть тот же профиль."""
    payload = credentials()
    first = client.post("/v1/auth/signup", json=payload).json()
    headers = {"Authorization": f"Bearer {first['accessToken']}"}
    client.patch("/v1/me/profile", headers=headers, json={"completeOnboarding": True})

    second = client.post("/v1/auth/signin", json=payload).json()
    assert second["user"]["userId"] == first["user"]["userId"]
    assert second["user"]["onboardingStatus"] == "complete"


# --- Google --------------------------------------------------------------------


def test_google_says_it_is_not_configured_rather_than_pretending(client):
    """Без Client ID проверять подпись нечем — и сервер так и отвечает."""
    assert settings.google_client_id is None
    response = client.post("/v1/auth/google", json={"idToken": "x" * 32})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "google_not_configured"


# --- Что сервер обещает ---------------------------------------------------------


def test_methods_reports_only_what_the_server_can_actually_do(client):
    methods = client.get("/v1/auth/methods").json()
    assert methods["password"] is True
    assert methods["google"] is False  # GOOGLE_CLIENT_ID не задан
    assert methods["apple"] is False   # APPLE_CLIENT_ID не задан
    assert methods["developer"] is True
    assert methods["googleClientId"] is None


def test_password_auth_can_be_switched_off(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_password_auth", False)
    assert client.get("/v1/auth/methods").json()["password"] is False
    assert client.post("/v1/auth/signup", json=credentials()).status_code == 404
    assert client.post("/v1/auth/signin", json=credentials()).status_code == 404
