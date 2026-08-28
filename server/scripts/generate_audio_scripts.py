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
import sys
import time

from app import tree_content
from app.ai.base import ProviderError
from app.services import audio, audio_script

# Бесплатный тариф Gemini ограничен примерно десятью запросами в минуту, поэтому
# по умолчанию идём медленнее лимита: упереться в 429 на середине корпуса дороже,
# чем подождать.
# Бесплатный тариф Gemini ограничен по частоте, поэтому по умолчанию идём медленнее
# лимита: упереться в 429 на середине корпуса дороже, чем подождать.
DEFAULT_DELAY = 7.0


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
            turns, provider, model = audio_script.generate(
                lesson, mock=args.mock, log=lambda m: print(f"      {m}", flush=True)
            )
        except ProviderError as error:
            failed += 1
            print(f"      не вышло: {error.code} {error}", flush=True)
            continue
        audio_script.write_script(lesson, turns, provider, model)
        written += 1
        print(f"      реплик: {len(turns)}  провайдер: {provider}", flush=True)
        if not args.mock and args.delay:
            time.sleep(args.delay)

    print(f"\nнаписано: {written}  уже было: {skipped}  не вышло: {failed}")
    if failed:
        print("Отклонённые уроки можно повторить — попытки независимы.")


if __name__ == "__main__":
    sys.exit(main())
