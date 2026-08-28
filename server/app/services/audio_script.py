# -*- coding: utf-8 -*-
"""Сценарий аудиообзора: генерация один раз, проверка фактов, хранение как контент.

Обзор пишется моделью, поэтому здесь же он и проверяется. Доверять модели факты
курса нельзя: она охотно округляет числа и придумывает аббревиатуры. Проверка
простая и жёсткая — всё, что выглядит как число или латинский термин, обязано
встречаться в тексте урока. Всё остальное (тон, живость, порядок) — забота
промпта, и проверить это кодом нельзя.

Генерация идёт на этапе сборки, а не по запросу: результат ложится в
`content/<дерево>/audio-scripts/` и дальше живёт как обычный контент, который
можно вычитать и поправить руками. Рантайм к провайдеру не ходит никогда.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.audio_prompt import PROMPT_VERSION, SYSTEM_PROMPT, user_prompt
from app.ai.base import EvaluationRequest, ProviderError

SPEAKERS = ("guide", "expert")
MIN_TURNS, MAX_TURNS = 6, 60

# Фразы, которые промпт запрещает, но модель всё равно приносит. Проверяются, потому
# что каждая из них выдаёт «озвученный текст» вместо разговора.
BANNED = (
    "здравствуйте",
    "добрый день",
    "сегодня мы поговорим",
    "в этом уроке",
    "аудиоверси",
    "друзья",
)


def lesson_body(lesson: dict) -> str:
    """Текст урока как его читает человек: без разметки, но без озвучных замен."""
    from app.services.audio import block_lines_for_prompt

    return "\n\n".join(block_lines_for_prompt(lesson))


def _numbers(text: str) -> set[str]:
    """Числа без разделителей: «8 000» и «8000» — одно и то же число."""
    joined = re.sub(r"(?<=\d)[   ](?=\d)", "", text)
    return {n.replace(",", ".").rstrip(".") for n in re.findall(r"\d+(?:[.,]\d+)?", joined)}


def _latin(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{1,}", text)}


def validate_script(turns: list[dict], lesson: dict) -> list[str]:
    """Возвращает список претензий. Пустой список — сценарий можно публиковать."""
    problems: list[str] = []
    if not MIN_TURNS <= len(turns) <= MAX_TURNS:
        problems.append(f"реплик {len(turns)}, нужно от {MIN_TURNS} до {MAX_TURNS}")

    speakers = {turn.get("speaker") for turn in turns}
    if not speakers <= set(SPEAKERS):
        problems.append(f"неизвестный говорящий: {speakers - set(SPEAKERS)}")
    elif len(speakers) < 2:
        problems.append("говорит только один — это не разговор")

    spoken = " ".join(turn.get("text", "") for turn in turns)
    if not spoken.strip():
        problems.append("пустой сценарий")

    source = lesson_body(lesson) + " " + lesson.get("title", "") + " " + lesson.get("keyTakeaway", "")

    invented_numbers = _numbers(spoken) - _numbers(source)
    if invented_numbers:
        problems.append(f"числа, которых нет в уроке: {sorted(invented_numbers)[:6]}")

    invented_terms = _latin(spoken) - _latin(source)
    if invented_terms:
        problems.append(f"термины, которых нет в уроке: {sorted(invented_terms)[:6]}")

    lowered = spoken.lower()
    said = [phrase for phrase in BANNED if phrase in lowered]
    if said:
        problems.append(f"запрещённые обороты: {said}")

    # Дословный кусок урока в реплике означает, что модель зачитывает, а не объясняет.
    for turn in turns:
        text = (turn.get("text") or "").strip()
        if len(text) > 120 and text[:120] in source:
            problems.append(f"дословная цитата урока: «{text[:60]}…»")
            break

    return problems


def parse_turns(raw: str) -> list[dict]:
    """Разбирает ответ модели. JSON может приехать в ```-заборе — это норма."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\s*|\s*```$", "", cleaned)
    try:
        payload: Any = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError("script_not_json", str(exc)[:200], retryable=True) from exc

    turns = payload.get("turns") if isinstance(payload, dict) else payload
    if not isinstance(turns, list):
        raise ProviderError("script_no_turns", "в ответе нет списка реплик", retryable=True)

    parsed = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        speaker = str(turn.get("speaker", "")).strip().lower()
        text = str(turn.get("text", "")).strip()
        if speaker in SPEAKERS and text:
            parsed.append({"speaker": speaker, "text": text})
    return parsed


def build_request(lesson: dict) -> EvaluationRequest:
    return EvaluationRequest(
        scenario_id=lesson["id"],
        scenario_version=int(lesson.get("version", 1)),
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt(
            title=lesson.get("title", ""),
            body=lesson_body(lesson),
            takeaway=lesson.get("keyTakeaway", ""),
        ),
    )


PROMPT = PROMPT_VERSION
