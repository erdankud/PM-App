"""Адаптер провайдера: что считается ответом, а что — обрывом.

Отдельно от `test_ai_validation.py`: там проверяется разбор текста, здесь — то,
что до разбора вообще доходит. Оба теста ниже написаны по реальному отказу:
разбор тренировки трижды падал как «модель не умеет в JSON», а на самом деле
Gemini списывал лимит вывода на собственное размышление и обрывал ответ на
середине поля.
"""

from __future__ import annotations

import json

import pytest

from app.ai import providers
from app.ai.base import EvaluationRequest, ProviderError


class _Response:
    def __init__(self, payload: dict) -> None:
        self.status_code = 200
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


def _candidate(text: str, finish_reason: str = "STOP", thoughts: int = 0) -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": finish_reason,
            }
        ],
        "usageMetadata": {"thoughtsTokenCount": thoughts},
    }


@pytest.fixture
def sent(monkeypatch):
    """Перехватывает запрос к провайдеру и отдаёт тело наружу."""
    captured: dict = {}
    payload: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update({"url": url, "body": json})
        return _Response(payload)

    monkeypatch.setattr(providers.httpx, "post", fake_post)
    monkeypatch.setattr(providers.settings, "evaluator_api_key", "test-key")
    monkeypatch.setattr(providers.settings, "evaluator_model", "gemini-test")
    captured["reply"] = payload
    return captured


REQUEST = EvaluationRequest(
    scenario_id="s1",
    scenario_version=1,
    system_prompt="system",
    user_prompt="user",
    max_output_tokens=1600,
)


def test_thinking_gets_its_own_budget(sent):
    """`max_output_tokens` наверху — это нужный текст, а не текст плюс мысли."""
    sent["reply"].update(_candidate('{"ok": true}'))
    providers.GeminiEvaluator().evaluate(REQUEST)
    limit = sent["body"]["generationConfig"]["maxOutputTokens"]
    assert limit == 1600 + providers.THINKING_ALLOWANCE


def test_truncated_output_is_not_passed_off_as_an_answer(sent):
    sent["reply"].update(_candidate('{"headline": "нача', "MAX_TOKENS", thoughts=1344))
    with pytest.raises(ProviderError) as exc:
        providers.GeminiEvaluator().evaluate(REQUEST)
    assert exc.value.code == "provider_output_truncated"
    assert exc.value.retryable is True
    # Число в сообщении — то, ради чего его читают: оно говорит, куда ушёл лимит.
    assert "1344" in str(exc.value)


def test_complete_output_passes_through(sent):
    sent["reply"].update(_candidate('{"headline": "готово"}'))
    response = providers.GeminiEvaluator().evaluate(REQUEST)
    assert json.loads(response.raw_text)["headline"] == "готово"
    assert response.model_id == "gemini-test"
