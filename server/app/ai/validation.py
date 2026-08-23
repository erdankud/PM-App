"""Validation of provider output.

Model output is untrusted until it has passed schema, length and range checks
(spec §13, §17). Anything that fails here is a provider error, not user-visible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.models import SKILL_KEYS
from app.services.scoring import (
    COMMUNICATION_MAX,
    RATIONALE_MAX,
    SKILL_DELTA_MAX,
    SKILL_DELTA_MIN,
)

MAX_TITLE = 60
MAX_DETAIL = 320
MAX_SHARPER = 700
MAX_ITEMS = 2

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class InvalidEvaluation(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class Evaluation:
    rationale_score: int
    communication_score: int
    strengths: list[dict[str, str]]
    improvements: list[dict[str, str]]
    sharper_approach: str
    skill_deltas: dict[str, int]
    needs_retry: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "rationale_score": self.rationale_score,
            "communication_score": self.communication_score,
            "strengths": self.strengths,
            "improvements": self.improvements,
            "sharper_approach": self.sharper_approach,
            "skill_deltas": self.skill_deltas,
            "needs_retry": self.needs_retry,
        }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK.search(cleaned)
    if match is None:
        raise InvalidEvaluation("output_not_json")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise InvalidEvaluation("output_not_json") from exc


def _clean_text(value: Any, limit: int, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidEvaluation("field_not_string", field)
    text = " ".join(value.split())
    if not text:
        raise InvalidEvaluation("field_empty", field)
    return text[:limit]


def _clean_items(value: Any, field: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidEvaluation("field_not_list", field)
    items: list[dict[str, str]] = []
    for entry in value[:MAX_ITEMS]:
        if not isinstance(entry, dict):
            raise InvalidEvaluation("item_not_object", field)
        items.append(
            {
                "title": _clean_text(entry.get("title"), MAX_TITLE, f"{field}.title"),
                "detail": _clean_text(entry.get("detail"), MAX_DETAIL, f"{field}.detail"),
            }
        )
    return items


def _clean_int(value: Any, low: int, high: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidEvaluation("field_not_number", field)
    number = int(round(float(value)))
    if number < low or number > high:
        raise InvalidEvaluation("field_out_of_range", field)
    return number


def parse_evaluation(raw_text: str) -> Evaluation:
    data = _extract_json(raw_text)
    if not isinstance(data, dict):
        raise InvalidEvaluation("output_not_object")

    rationale = _clean_int(data.get("rationale_score"), 0, RATIONALE_MAX, "rationale_score")
    communication = _clean_int(
        data.get("communication_score"), 0, COMMUNICATION_MAX, "communication_score"
    )

    deltas_raw = data.get("skill_deltas")
    if not isinstance(deltas_raw, dict):
        raise InvalidEvaluation("skill_deltas_missing")
    deltas: dict[str, int] = {}
    for key in SKILL_KEYS:
        deltas[key] = _clean_int(
            deltas_raw.get(key, 0), SKILL_DELTA_MIN, SKILL_DELTA_MAX, f"skill_deltas.{key}"
        )
    unknown = set(deltas_raw) - set(SKILL_KEYS)
    if unknown:
        raise InvalidEvaluation("skill_deltas_unknown_key", ",".join(sorted(unknown)))

    strengths = _clean_items(data.get("strengths"), "strengths")
    improvements = _clean_items(data.get("improvements"), "improvements")
    sharper = _clean_text(data.get("sharper_approach"), MAX_SHARPER, "sharper_approach")

    needs_retry = data.get("needs_retry", False)
    if not isinstance(needs_retry, bool):
        raise InvalidEvaluation("needs_retry_not_bool")

    if not needs_retry and not strengths and not improvements:
        raise InvalidEvaluation("coaching_empty")

    return Evaluation(
        rationale_score=rationale,
        communication_score=communication,
        strengths=strengths,
        improvements=improvements,
        sharper_approach=sharper,
        skill_deltas=deltas,
        needs_retry=needs_retry,
    )
