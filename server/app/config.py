"""Server configuration.

Everything secret lives here and only here. The iOS client never receives, embeds,
or proxies an AI provider key (spec §17, quality acceptance in §21).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Core ---------------------------------------------------------------
    environment: str = "development"
    api_prefix: str = "/v1"
    database_url: str = f"sqlite:///{SERVER_ROOT / 'pmcoach.db'}"

    # --- Audio ---------------------------------------------------------------
    # Сценарист аудиообзоров. Ключ тот же, что у оценщика: это один и тот же
    # аккаунт провайдера, а генерация идёт только на этапе сборки контента.
    audio_script_model: str | None = "gemini-3.6-flash"
    # Цепочка моделей переводчика. У бесплатного тарифа квота считается **на
    # модель**, поэтому исчерпав одну, прогон переходит к следующей, а не встаёт
    # до завтра. Порядок — по убыванию качества; на этом корпусе разница между
    # ними неразличима, что проверено сравнением перевода одного урока.
    #
    # Отдельно от сценариста аудио: перевод упирается в квоту, сборка обзоров —
    # нет, и делить один лимит на двоих незачем.
    translation_models: list[str] = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
    ]
    # Кнопка «Сгенерировать обзор» в приложении. Авторский инструмент: включён в
    # разработке, выключен в релизе. Наружу его открывать нельзя, пока нет очереди
    # и ограничения частоты на пользователя.
    allow_audio_generation: bool = False
    # Готовые обзоры лежат вне репозитория: корпус в mp3 занимает около 300 МБ.
    # API их только раздаёт и сам ничего не синтезирует.
    audio_dir: str = str(SERVER_ROOT / "var" / "audio")

    # --- Auth ---------------------------------------------------------------
    # Override in every deployed environment.
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 60

    # Sign in with Apple. Without apple_client_id the endpoint returns 503 rather
    # than pretending to verify anything.
    apple_client_id: str | None = None
    apple_issuer: str = "https://appleid.apple.com"
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"

    # Sign in with Google. Бесплатен: нужен только Client ID из Google Cloud
    # Console, биллинг не требуется. Без него `/auth/google` отвечает 503 —
    # проверять подпись нечем, и делать вид, что проверили, нельзя.
    google_client_id: str | None = None
    # У мобильного клиента Client ID свой, а аккаунт тот же: обе аудитории
    # принимаются одним эндпоинтом.
    google_ios_client_id: str | None = None
    google_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"

    # Вход по почте и паролю. Существует потому, что Google Client ID заводится
    # руками в консоли, а продукт должен работать и до этого.
    allow_password_auth: bool = True

    # Dev-only identity path so the client can be exercised before Apple auth is
    # configured. MUST be false in production.
    allow_dev_auth: bool = True

    # --- Content ------------------------------------------------------------
    content_dir: Path = SERVER_ROOT / "content"

    # --- Evaluation ---------------------------------------------------------
    # Which EvaluatorProvider adapter to use. See app/ai/registry.py.
    #   mock       - deterministic offline evaluator, DEVELOPMENT ONLY.
    #   gemini     - Google Gemini API (has a free tier).
    #   groq       - Groq OpenAI-compatible API (has a free tier).
    #   openrouter - OpenRouter, including its :free model ids.
    #   anthropic  - Anthropic Messages API (paid).
    #   openai     - OpenAI Chat Completions API (paid).
    evaluator_provider: str = "mock"
    evaluator_model: str | None = None
    evaluator_api_key: str | None = None
    evaluator_base_url: str | None = None
    evaluator_timeout_seconds: float = 45.0
    evaluator_max_attempts: int = 3  # 1 initial + 2 retries (spec §13)
    evaluator_backoff_seconds: float = 2.0
    evaluations_per_user_per_day: int = 20

    # Background worker
    run_inline_worker: bool = True
    worker_poll_seconds: float = 1.5

    # --- Product rules (server-owned, spec §12) -----------------------------
    xp_base_completion: int = 50
    xp_quality_bonus_cap: int = 50
    xp_lesson_completed: int = 10
    # A gate is passed on the total, never on one component: option choice plus full
    # evidence review caps out at 40, so no one passes without writing (spec v0.2 §9).
    gate_pass_threshold: int = 70
    # Recalibrated for ~140 lessons and 18 gates rather than a daily challenge.
    level_thresholds: list[int] = [0, 150, 400, 800, 1400, 2200]
    level_step_after_thresholds: int = 800
    path_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.jwt_secret == "dev-only-insecure-secret-change-me":
            raise RuntimeError("JWT_SECRET must be set in production")
        if settings.allow_dev_auth:
            raise RuntimeError("ALLOW_DEV_AUTH must be false in production")
        if settings.evaluator_provider == "mock":
            raise RuntimeError(
                "EVALUATOR_PROVIDER=mock is a development stub and must not be used "
                "in production; configure a real provider."
            )
    return settings


settings = get_settings()
