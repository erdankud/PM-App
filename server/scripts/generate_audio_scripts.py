# -*- coding: utf-8 -*-
"""Пишет сценарии аудиообзоров — по одному разговору на урок.

Обзор в стиле NotebookLM нельзя собрать из текста перестановкой: разговорный
регистр надо написать. Поэтому диалог пишет модель — но ровно один раз, на этапе
сборки. Результат ложится в `content/<дерево>/audio-scripts/` как обычный контент:
его можно вычитать, поправить руками и посмотреть в диффе. Рантайм к провайдеру
не ходит никогда.

    export EVALUATOR_API_KEY=...                  # ключ Google AI Studio
    python -m scripts.generate_audio_scripts ds1-n1-l1   # один урок
    python -m scripts.generate_audio_scripts             # весь корпус
    python -m scripts.generate_audio_scripts --mock      # без ключа, заглушка

Модель проверяется, а не принимается на веру: числа и латинские термины из
диалога обязаны встречаться в уроке, иначе попытка не засчитывается и повторяется.
Бесплатный тариф ограничен по частоте, поэтому между запросами выдерживается пауза.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from app import tree_content
from app.ai.audio_prompt import PROMPT_VERSION, SYSTEM_PROMPT, user_prompt
from app.ai.base import ProviderError
from app.services import audio, audio_script

# Бесплатный тариф Gemini ограничен примерно десятью запросами в минуту, поэтому
# по умолчанию идём медленнее лимита: упереться в 429 на середине корпуса дороже,
# чем подождать.
DEFAULT_DELAY = 7.0
MAX_ATTEMPTS = 3


def mock_turns(lesson: dict) -> list[dict]:
    """Заглушка без провайдера: разговором не является и не притворяется им.

    Нужна ровно для одного — прогнать конвейер и тесты там, где ключа нет. Всё,
    что она делает, это раздаёт авторский текст двум голосам по очереди.
    """
    lines = audio.block_lines_for_prompt(lesson)[:8]
    turns = [{"speaker": "guide", "text": f"Разберём урок «{lesson['title']}». С чего начать?"}]
    for index, line in enumerate(lines):
        turns.append({"speaker": "expert" if index % 2 == 0 else "guide", "text": line[:880]})
    if lesson.get("keyTakeaway"):
        turns.append({"speaker": "expert", "text": lesson["keyTakeaway"][:880]})
    return turns


def generate(lesson: dict, *, mock: bool) -> tuple[list[dict], str, str]:
    """Возвращает (реплики, провайдер, модель). Бросает, если не вышло."""
    if mock:
        return mock_turns(lesson), "mock", "mock"

    from app.ai.providers import gemini_text

    problems: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = user_prompt(
            title=lesson.get("title", ""),
            body=audio_script.lesson_body(lesson),
            takeaway=lesson.get("keyTakeaway", ""),
        )
        if problems:
            # Претензии возвращаются модели: без них вторая попытка повторяет ошибку.
            prompt += "\n\nПрошлая попытка отклонена: " + "; ".join(problems) + ". Исправь."
        raw, model_id = gemini_text(SYSTEM_PROMPT, prompt)
        turns = audio_script.parse_turns(raw)
        problems = audio_script.validate_script(turns, lesson)
        if not problems:
            return turns, "gemini", model_id
        print(f"      попытка {attempt}: {'; '.join(problems)}", flush=True)
    raise ProviderError("script_rejected", "; ".join(problems), retryable=False)


def write_script(lesson: dict, turns: list[dict], provider: str, model: str) -> Path:
    path = audio.script_path(lesson)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lessonId": lesson["id"],
        "sourceDigest": audio.source_digest(lesson),
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


def lessons_for(names: list[str]) -> list[dict]:
    if names:
        found = []
        for name in names:
            lesson = tree_content.lesson(name)
            if lesson is None:
                raise SystemExit(f"нет урока {name}")
            found.append(lesson)
        return found
    return [
        lesson
        for kind in tree_content.KINDS
        for lesson in tree_content.tree_content(kind)["lessons"].values()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lessons", nargs="*", help="идентификаторы уроков; пусто — все")
    parser.add_argument("--mock", action="store_true", help="заглушка без провайдера")
    parser.add_argument("--force", action="store_true", help="переписать даже свежие сценарии")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="пауза между запросами")
    parser.add_argument("--limit", type=int, help="остановиться после N сгенерированных")
    args = parser.parse_args()

    targets = lessons_for(args.lessons)
    written = skipped = failed = 0

    for index, lesson in enumerate(targets, start=1):
        if not args.force and audio.load_script(lesson) is not None:
            skipped += 1
            continue
        if args.limit and written >= args.limit:
            break
        print(f"[{index:3}/{len(targets)}] {lesson['id']}", flush=True)
        try:
            turns, provider, model = generate(lesson, mock=args.mock)
        except ProviderError as error:
            failed += 1
            print(f"      не вышло: {error.code} {error}", flush=True)
            continue
        write_script(lesson, turns, provider, model)
        written += 1
        print(f"      реплик: {len(turns)}  провайдер: {provider}", flush=True)
        if not args.mock and args.delay:
            time.sleep(args.delay)

    print(f"\nнаписано: {written}  уже было: {skipped}  не вышло: {failed}")
    if failed:
        print("Отклонённые уроки можно повторить — попытки независимы.")


if __name__ == "__main__":
    sys.exit(main())
