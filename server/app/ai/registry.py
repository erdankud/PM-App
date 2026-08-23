"""Provider selection. Changing evaluator is a configuration change only."""

from __future__ import annotations

from functools import lru_cache

from app.ai.base import EvaluatorProvider
from app.ai.mock import MockEvaluator
from app.ai.providers import (
    AnthropicEvaluator,
    GeminiEvaluator,
    OpenAICompatibleEvaluator,
)
from app.config import settings

_FACTORIES = {
    "mock": MockEvaluator,
    "gemini": GeminiEvaluator,
    "anthropic": AnthropicEvaluator,
    "groq": lambda: OpenAICompatibleEvaluator(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
    ),
    "openrouter": lambda: OpenAICompatibleEvaluator(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
    ),
    "openai": lambda: OpenAICompatibleEvaluator(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
}

AVAILABLE_PROVIDERS = tuple(sorted(_FACTORIES))


@lru_cache
def get_provider() -> EvaluatorProvider:
    key = (settings.evaluator_provider or "mock").strip().lower()
    factory = _FACTORIES.get(key)
    if factory is None:
        raise RuntimeError(
            f"Unknown EVALUATOR_PROVIDER '{key}'. "
            f"Available: {', '.join(AVAILABLE_PROVIDERS)}"
        )
    return factory()
