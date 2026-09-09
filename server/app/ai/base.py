"""Provider-agnostic evaluation interface.

Everything above this layer deals in `EvaluationRequest` / raw JSON text. Swapping
providers is a configuration change, never an application change, and no provider
key is ever visible to the iOS client (spec §13, §17).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

PROMPT_VERSION = "eval-2026-08-23"  # adds the output-language rule
PRACTICE_PROMPT_VERSION = "practice-2026-09-09"  # первый выпуск модуля Practice


@dataclass(frozen=True)
class EvaluationRequest:
    scenario_id: str
    scenario_version: int
    system_prompt: str
    user_prompt: str
    # Present so mock/offline evaluators can produce a plausible response without
    # re-parsing the prompt. Real providers ignore it.
    context: dict = field(default_factory=dict)
    # Оценка и генерация — разные задачи для одной и той же модели. Разбор обязан
    # быть воспроизводимым и коротким, а сценарий тренировки — наоборот, каждый раз
    # другим: две подряд одинаковые задачи Practice убивают весь смысл кнопки
    # «сгенерировать следующую». Значения по умолчанию — ровно те, с которыми
    # адаптеры жили до появления этих полей, поэтому оценка гейта не меняется.
    temperature: float = 0.3
    max_output_tokens: int = 1600


@dataclass(frozen=True)
class ProviderResponse:
    raw_text: str
    model_id: str


class QuotaExhausted(RuntimeError):
    """Дневная квота провайдера исчерпана.

    Отдельно от `ProviderError`, потому что реакция другая: повторять бессмысленно
    ни сейчас, ни следующим файлом. Прогон обязан остановиться, а не пройти по
    остатку корпуса, пометив всё несделанным.
    """


class ProviderError(RuntimeError):
    """Transient or permanent provider failure. `code` is logged, never shown."""

    def __init__(self, code: str, message: str = "", retryable: bool = True) -> None:
        super().__init__(message or code)
        self.code = code
        self.retryable = retryable


class EvaluatorProvider(Protocol):
    name: str

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        """Return the provider's raw response text (expected to be JSON)."""
        ...
