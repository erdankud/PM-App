"""HTTP evaluator adapters.

All of them take the same `EvaluationRequest` and return raw response text for
`app.ai.validation` to check. API keys are read from server settings only.

Free-tier friendly defaults:
  gemini      Google AI Studio has a free tier (rate limited).
  groq        Groq's API has a free tier.
  openrouter  Model ids ending in ":free" cost nothing.
Paid adapters (anthropic, openai) are included so the choice is a config change.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.ai.base import EvaluationRequest, ProviderError, ProviderResponse
from app.config import settings

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _require_key() -> str:
    if not settings.evaluator_api_key:
        raise ProviderError(
            "provider_not_configured",
            "EVALUATOR_API_KEY is not set",
            retryable=False,
        )
    return settings.evaluator_api_key


def _post(url: str, *, headers: dict[str, str], json_body: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(
            url,
            headers=headers,
            json=json_body,
            timeout=settings.evaluator_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise ProviderError("provider_timeout", str(exc), retryable=True) from exc
    except httpx.HTTPError as exc:
        raise ProviderError("provider_unreachable", str(exc), retryable=True) from exc

    if response.status_code >= 400:
        raise ProviderError(
            f"provider_http_{response.status_code}",
            response.text[:400],
            retryable=response.status_code in _RETRYABLE_STATUS,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("provider_bad_payload", retryable=True) from exc


class GeminiEvaluator:
    name = "gemini"
    default_model = "gemini-2.0-flash"

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        key = _require_key()
        model = settings.evaluator_model or self.default_model
        base = settings.evaluator_base_url or "https://generativelanguage.googleapis.com"
        url = f"{base}/v1beta/models/{model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.user_prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1600,
                "responseMimeType": "application/json",
            },
        }
        payload = _post(url, headers={"x-goog-api-key": key}, json_body=body)
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("provider_empty_response", retryable=True) from exc
        if not text.strip():
            raise ProviderError("provider_empty_response", retryable=True)
        return ProviderResponse(raw_text=text, model_id=model)


def gemini_text(
    system_prompt: str,
    user_prompt_text: str,
    *,
    model: str | None = None,
    max_output_tokens: int = 4096,
    temperature: float = 0.9,
) -> tuple[str, str]:
    """Свободная генерация текста через Gemini: возвращает (текст, id модели).

    Отдельно от `GeminiEvaluator`, потому что задачи разные. Оценка обязана быть
    воспроизводимой и короткой, а сценарий обзора — наоборот, живым и длинным:
    отсюда высокая температура и большой лимит вывода.
    """
    key = _require_key()
    model_id = model or settings.audio_script_model or "gemini-3.6-flash"
    base = settings.evaluator_base_url or "https://generativelanguage.googleapis.com"
    url = f"{base}/v1beta/models/{model_id}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt_text}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    payload = _post(url, headers={"x-goog-api-key": key}, json_body=body)
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("provider_empty_response", retryable=True) from exc
    if not text.strip():
        raise ProviderError("provider_empty_response", retryable=True)
    return text, model_id


class OpenAICompatibleEvaluator:
    """Chat Completions shape: OpenAI, Groq, OpenRouter, and most local servers."""

    def __init__(self, name: str, base_url: str, default_model: str) -> None:
        self.name = name
        self._base_url = base_url
        self._default_model = default_model

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        key = _require_key()
        model = settings.evaluator_model or self._default_model
        base = settings.evaluator_base_url or self._base_url
        headers = {"Authorization": f"Bearer {key}"}
        if self.name == "openrouter":
            headers["X-Title"] = "PM Thinking Coach"
        body = {
            "model": model,
            "temperature": 0.3,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        payload = _post(f"{base}/chat/completions", headers=headers, json_body=body)
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("provider_empty_response", retryable=True) from exc
        if not text or not text.strip():
            raise ProviderError("provider_empty_response", retryable=True)
        return ProviderResponse(raw_text=text, model_id=model)


class AnthropicEvaluator:
    name = "anthropic"
    default_model = "claude-sonnet-4-5"

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        key = _require_key()
        model = settings.evaluator_model or self.default_model
        base = settings.evaluator_base_url or "https://api.anthropic.com"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": 1600,
            "temperature": 0.3,
            "system": request.system_prompt,
            "messages": [
                {"role": "user", "content": request.user_prompt},
                # Prefilling the opening brace keeps the response to JSON only.
                {"role": "assistant", "content": "{"},
            ],
        }
        payload = _post(f"{base}/v1/messages", headers=headers, json_body=body)
        try:
            blocks = payload["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise ProviderError("provider_empty_response", retryable=True) from exc
        if not text.strip():
            raise ProviderError("provider_empty_response", retryable=True)
        return ProviderResponse(raw_text="{" + text, model_id=model)
