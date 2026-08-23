"""Provider-agnostic evaluation interface.

Everything above this layer deals in `EvaluationRequest` / raw JSON text. Swapping
providers is a configuration change, never an application change, and no provider
key is ever visible to the iOS client (spec §13, §17).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

PROMPT_VERSION = "eval-2026-08-01"


@dataclass(frozen=True)
class EvaluationRequest:
    scenario_id: str
    scenario_version: int
    system_prompt: str
    user_prompt: str
    # Present so mock/offline evaluators can produce a plausible response without
    # re-parsing the prompt. Real providers ignore it.
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    raw_text: str
    model_id: str


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
