"""Проверка того, что вернула модель в модуле Practice.

Вывод модели недоверенный, пока не прошёл проверку — то же правило, что у оценки
гейта и у переводчика. Здесь оно важнее обычного: и задача, и разбор попадают на
экран целиком, без авторской редактуры между. Поэтому проверяется не только форма,
но и то, ради чего поле существует: задача без ключевого вопроса — не задача,
разбор без оценки по каждому шагу канвы — не разбор этой канвы.

Всё, что не прошло, — ошибка провайдера, а не ошибка человека: попытка повторяется,
пользователь об этом не узнаёт.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.practice_catalogue import Track

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

# Виды задачи проверяются по словарю направления, а не по общему списку: «diagnose»
# в аналитике и «diagnose» в продуктовом чутье — разные задачи, и общий список
# пропустил бы вид, для которого у направления нет ни правил, ни канвы.
BARS = {"below", "at", "above"}

MAX_TITLE = 80
MAX_COMPANY = 80
MAX_CONTEXT = 900
MAX_PROMPT = 320
MAX_CONSTRAINT = 160
MAX_CLARIFIER_Q = 180
MAX_CLARIFIER_A = 320
MAX_HEADLINE = 200
MAX_NOTE = 320
MAX_ITEM_TITLE = 60
MAX_ITEM_DETAIL = 320
MAX_MISSED = 280
MAX_SHARPER = 1000
MAX_COUNTER = 480


class InvalidPracticeOutput(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(cleaned)
        if match is None:
            raise InvalidPracticeOutput("output_not_json") from None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise InvalidPracticeOutput("output_not_json") from exc
    if not isinstance(data, dict):
        raise InvalidPracticeOutput("output_not_object")
    return data


def _text(value: Any, limit: int, field: str, *, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise InvalidPracticeOutput("field_not_string", field)
    collapsed = " ".join(value.split())
    if len(collapsed) < minimum:
        raise InvalidPracticeOutput("field_too_short", field)
    return collapsed[:limit]


def _string_list(value: Any, limit: int, field: str, *, low: int, high: int) -> list[str]:
    if not isinstance(value, list):
        raise InvalidPracticeOutput("field_not_list", field)
    items = [_text(entry, limit, field) for entry in value[:high]]
    if len(items) < low:
        raise InvalidPracticeOutput("list_too_short", field)
    return items


def _items(value: Any, field: str, *, low: int, high: int) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise InvalidPracticeOutput("field_not_list", field)
    items: list[dict[str, str]] = []
    for entry in value[:high]:
        if not isinstance(entry, dict):
            raise InvalidPracticeOutput("item_not_object", field)
        items.append(
            {
                "title": _text(entry.get("title"), MAX_ITEM_TITLE, f"{field}.title"),
                "detail": _text(entry.get("detail"), MAX_ITEM_DETAIL, f"{field}.detail"),
            }
        )
    if len(items) < low:
        raise InvalidPracticeOutput("list_too_short", field)
    return items


def parse_brief(raw_text: str, track: Track) -> dict[str, Any]:
    data = _extract_json(raw_text)

    kind = data.get("kind")
    if kind not in track.kinds:
        raise InvalidPracticeOutput("brief_kind_unknown", str(kind)[:40])

    clarifiers_raw = data.get("clarifiers")
    if not isinstance(clarifiers_raw, list):
        raise InvalidPracticeOutput("field_not_list", "clarifiers")
    clarifiers: list[dict[str, str]] = []
    for entry in clarifiers_raw[:5]:
        if not isinstance(entry, dict):
            raise InvalidPracticeOutput("item_not_object", "clarifiers")
        clarifiers.append(
            {
                "question": _text(entry.get("question"), MAX_CLARIFIER_Q, "clarifiers.question"),
                "answer": _text(entry.get("answer"), MAX_CLARIFIER_A, "clarifiers.answer"),
            }
        )
    # Меньше двух уточнений — это уже не «спроси, если нужно», а декорация:
    # у человека нет выбора, который он мог бы сделать.
    if len(clarifiers) < 2:
        raise InvalidPracticeOutput("list_too_short", "clarifiers")

    brief: dict[str, Any] = {
        "title": _text(data.get("title"), MAX_TITLE, "title", minimum=4),
        "company": _text(data.get("company"), MAX_COMPANY, "company", minimum=2),
        "kind": kind,
        "context": _text(data.get("context"), MAX_CONTEXT, "context", minimum=80),
        # Задача без самого вопроса — не задача. Нижняя граница здесь не про длину,
        # а про то, что модель иногда возвращает «Design it.» и уходит.
        "prompt": _text(data.get("prompt"), MAX_PROMPT, "prompt", minimum=20),
        "constraints": _string_list(
            data.get("constraints"), MAX_CONSTRAINT, "constraints", low=2, high=4
        ),
        "clarifiers": clarifiers,
    }

    # Возражение обязательно там, где на него отвечают полем канвы: задача без него
    # оставила бы человека перед пустым полем «ответьте на возражение».
    if track.counter_field is not None:
        brief["counter"] = _text(data.get("counter"), MAX_COUNTER, "counter", minimum=40)

    return brief


def parse_feedback(raw_text: str, track: Track) -> dict[str, Any]:
    data = _extract_json(raw_text)

    bar = data.get("bar")
    if bar not in BARS:
        raise InvalidPracticeOutput("bar_unknown", str(bar)[:40])

    fields_raw = data.get("fields")
    if not isinstance(fields_raw, list):
        raise InvalidPracticeOutput("field_not_list", "fields")
    by_id: dict[str, dict[str, Any]] = {}
    for entry in fields_raw:
        if not isinstance(entry, dict):
            raise InvalidPracticeOutput("item_not_object", "fields")
        field_id = entry.get("id")
        if not isinstance(field_id, str):
            raise InvalidPracticeOutput("field_not_string", "fields.id")
        score = entry.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise InvalidPracticeOutput("field_not_number", "fields.score")
        score = int(round(float(score)))
        if score < 0 or score > 5:
            raise InvalidPracticeOutput("field_out_of_range", "fields.score")
        by_id[field_id] = {
            "id": field_id,
            "score": score,
            "note": _text(entry.get("note"), MAX_NOTE, "fields.note"),
        }

    # Порядок разбора — это порядок канвы, а не порядок, в котором модель решила
    # отвечать: человек читает разбор рядом со своим ответом, поле в поле.
    missing = [item.id for item in track.canvas if item.id not in by_id]
    if missing:
        raise InvalidPracticeOutput("fields_missing", ",".join(missing))
    ordered = [by_id[item.id] for item in track.canvas]

    return {
        "headline": _text(data.get("headline"), MAX_HEADLINE, "headline", minimum=10),
        "bar": bar,
        "fields": ordered,
        "strengths": _items(data.get("strengths"), "strengths", low=1, high=2),
        "improvements": _items(data.get("improvements"), "improvements", low=1, high=2),
        "missed_question": _text(
            data.get("missed_question"), MAX_MISSED, "missed_question", minimum=10
        ),
        "sharper_approach": _text(
            data.get("sharper_approach"), MAX_SHARPER, "sharper_approach", minimum=60
        ),
    }
