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

from app.ai.audio_prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    SYSTEM_PROMPTS,
    USER_PROMPTS,
    user_prompt,
)
from app.ai.base import EvaluationRequest, ProviderError

SPEAKERS = ("guide", "expert")
MIN_TURNS, MAX_TURNS = 6, 60

# Фразы, которые промпт запрещает, но модель всё равно приносит. Проверяются, потому
# что каждая из них выдаёт «озвученный текст» вместо разговора.
BANNED = {
    "ru": (
        "здравствуйте",
        "добрый день",
        "сегодня мы поговорим",
        "в этом уроке",
        "аудиоверси",
        "друзья",
    ),
    "en": (
        "hello everyone",
        "welcome back",
        "today we are going to talk about",
        "today we're going to talk about",
        "in this lesson",
        "audio version",
        "folks",
    ),
}


def lesson_body(lesson: dict, language: str = "ru") -> str:
    """Текст урока как его читает человек: без разметки, но без озвучных замен."""
    from app.services.audio import block_lines_for_prompt

    return "\n\n".join(block_lines_for_prompt(lesson, language))


def _numbers(text: str) -> set[str]:
    """Числа без разделителей: «8 000» и «8000» — одно и то же число."""
    joined = re.sub(r"(?<=\d)[   ](?=\d)", "", text)
    return {n.replace(",", ".").rstrip(".") for n in re.findall(r"\d+(?:[.,]\d+)?", joined)}


def _latin(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_.-]{1,}", text)}


def validate_script(turns: list[dict], lesson: dict, language: str = "ru") -> list[str]:
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

    source = (
        lesson_body(lesson, language)
        + " "
        + lesson.get("title", "")
        + " "
        + lesson.get("keyTakeaway", "")
    )

    invented_numbers = _numbers(spoken) - _numbers(source)
    if invented_numbers:
        problems.append(f"числа, которых нет в уроке: {sorted(invented_numbers)[:6]}")

    invented_terms = _latin(spoken) - _latin(source)
    if language == "en":
        # В английском уроке латиница — это весь текст, а не только термины:
        # сверять пословно бессмысленно. Числа проверяются как и раньше.
        invented_terms = set()
    if invented_terms:
        problems.append(f"термины, которых нет в уроке: {sorted(invented_terms)[:6]}")

    lowered = spoken.lower()
    said = [phrase for phrase in BANNED.get(language, BANNED["ru"]) if phrase in lowered]
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


def build_request(lesson: dict, language: str = "ru") -> EvaluationRequest:
    return EvaluationRequest(
        scenario_id=lesson["id"],
        scenario_version=int(lesson.get("version", 1)),
        system_prompt=SYSTEM_PROMPTS.get(language, SYSTEM_PROMPT),
        user_prompt=USER_PROMPTS.get(language, user_prompt)(
            title=lesson.get("title", ""),
            body=lesson_body(lesson, language),
            takeaway=lesson.get("keyTakeaway", ""),
        ),
    )


PROMPT = PROMPT_VERSION


# --- Генерация ---------------------------------------------------------------
#
# Живёт в сервисе, а не в скрипте, потому что генерацию запускает и скрипт сборки,
# и — в дев-сборке — кнопка в приложении. Провайдер вызывается только отсюда.

MAX_ATTEMPTS = 3


def mock_turns(lesson: dict, language: str = "ru") -> list[dict]:
    """Заглушка без провайдера: разговором не является и не притворяется им.

    Нужна ровно для одного — прогнать конвейер там, где ключа нет. Всё, что она
    делает, это раздаёт авторский текст двум голосам по очереди, поэтому проверку
    она намеренно не проходит.
    """
    from app.services.audio import block_lines_for_prompt

    lines = block_lines_for_prompt(lesson, language)[:8]
    opening = (
        f"Разберём урок «{lesson['title']}». С чего начать?"
        if language == "ru"
        else f"Let us take the lesson \"{lesson['title']}\". Where do we start?"
    )
    turns = [{"speaker": "guide", "text": opening}]
    for index, line in enumerate(lines):
        turns.append({"speaker": "expert" if index % 2 == 0 else "guide", "text": line[:880]})
    if lesson.get("keyTakeaway"):
        turns.append({"speaker": "expert", "text": lesson["keyTakeaway"][:880]})
    return turns


def generate(
    lesson: dict, *, mock: bool = False, log=None, language: str = "ru"
) -> tuple[list[dict], str, str]:
    """Пишет диалог и проверяет его. Возвращает (реплики, провайдер, модель).

    Претензии проверки возвращаются модели следующей попыткой: без них вторая
    попытка повторяет ту же ошибку.
    """
    if mock:
        return mock_turns(lesson, language), "mock", "mock"

    from app.ai.providers import gemini_text

    system = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPT)
    build = USER_PROMPTS.get(language, user_prompt)
    complaint = (
        "\n\nПрошлая попытка отклонена: {}. Исправь."
        if language == "ru"
        else "\n\nThe previous attempt was rejected: {}. Fix it."
    )

    problems: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = build(
            title=lesson.get("title", ""),
            body=lesson_body(lesson, language),
            takeaway=lesson.get("keyTakeaway", ""),
        )
        if problems:
            prompt += complaint.format("; ".join(problems))
        raw, model_id = gemini_text(system, prompt)
        turns = parse_turns(raw)
        problems = validate_script(turns, lesson, language)
        if not problems:
            return turns, "gemini", model_id
        if log:
            log(f"попытка {attempt}: {'; '.join(problems)}")
    raise ProviderError("script_rejected", "; ".join(problems), retryable=False)


def write_script(
    lesson: dict, turns: list[dict], provider: str, model: str, language: str = "ru"
):
    from datetime import datetime, timezone

    from app.services.audio import script_path, source_digest

    path = script_path(lesson, language)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lessonId": lesson["id"],
        "sourceDigest": source_digest(lesson, language),
        "generator": {
            "provider": provider,
            "model": model,
            "promptVersion": PROMPT_VERSION,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "turns": turns,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
