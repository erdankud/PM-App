# -*- coding: utf-8 -*-
"""Готовит аудиоверсии уроков заранее.

Синтез идёт примерно в 25 раз быстрее реального времени, но урок на 12 минут — это
всё равно полминуты ожидания, и делать это в момент запроса значит показать
человеку спиннер вместо кнопки. Поэтому файлы собираются заранее, а раздача
становится отдачей статики.

    python -m scripts.build_audio --download   # голос, 63 МБ, один раз
    python -m scripts.build_audio              # весь корпус
    python -m scripts.build_audio ds1-n1-l1    # один урок

Повторный запуск дёшев: имя файла содержит хеш сценария, поэтому пересчитываются
только те уроки, текст которых изменился. Устаревшие файлы удаляются — иначе
каталог накапливает по mp3 на каждую редакцию урока.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from app import tree_content
from app.config import settings
from app.services import audio


def download_voice() -> None:
    target = Path(settings.audio_voice_dir)
    target.mkdir(parents=True, exist_ok=True)
    from piper.download_voices import download_voice as fetch

    print(f"качаю голос {audio.VOICE} в {target}")
    fetch(audio.VOICE, target)
    print("готово")


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
    parser.add_argument("--download", action="store_true", help="скачать голос и выйти")
    parser.add_argument(
        "--keep-stale",
        action="store_true",
        help="не удалять файлы отредактированных уроков (по умолчанию удаляются)",
    )
    args = parser.parse_args()

    if args.download:
        download_voice()
        return

    if not audio.voice_available():
        raise SystemExit(
            f"нет голоса {audio.VOICE}. Сначала: python -m scripts.build_audio --download"
        )

    targets = lessons_for(args.lessons)
    wanted = {audio.audio_path(lesson).name for lesson in targets}
    built = skipped = 0
    started = time.time()

    for index, lesson in enumerate(targets, start=1):
        path = audio.audio_path(lesson)
        if path.exists():
            skipped += 1
            continue
        mark = time.time()
        audio.synthesize(lesson)
        built += 1
        size = path.stat().st_size / 1024
        print(
            f"[{index:3}/{len(targets)}] {lesson['id']:<24} "
            f"{size:6.0f} КБ  {time.time() - mark:5.1f} с",
            flush=True,
        )

    removed = 0
    # Устаревшее чистится только при полном прогоне: при сборке одного урока
    # остальные файлы не «лишние», их просто не просили.
    if not args.keep_stale and not args.lessons:
        for stale in Path(settings.audio_dir).glob("*.mp3"):
            if stale.name not in wanted:
                stale.unlink()
                removed += 1

    total = sum(p.stat().st_size for p in Path(settings.audio_dir).glob("*.mp3"))
    print(
        f"\nсобрано: {built}  уже было: {skipped}  удалено устаревших: {removed}  "
        f"время: {time.time() - started:.0f} с  каталог: {total / 1024 / 1024:.0f} МБ"
    )


if __name__ == "__main__":
    sys.exit(main())
