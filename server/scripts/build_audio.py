# -*- coding: utf-8 -*-
"""Готовит аудиоверсии уроков заранее.

Синтез идёт по сети и занимает около минуты на урок, поэтому делать его в момент
запроса значит показать человеку спиннер вместо кнопки. Файлы собираются заранее,
а раздача становится отдачей статики — и тогда недоступность сервиса синтеза
ломает только сборку новых обзоров, а не выдачу уже собранных.

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


def lessons_for(names: list[str], language: str = "ru") -> list[dict]:
    if names:
        found = []
        for name in names:
            lesson = tree_content.lesson(name, language)
            if lesson is None:
                raise SystemExit(f"нет урока {name}")
            found.append(lesson)
        return found
    return [
        lesson
        for kind in tree_content.KINDS
        for lesson in tree_content.tree_content(kind, language)["lessons"].values()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lessons", nargs="*", help="идентификаторы уроков; пусто — все")
    parser.add_argument(
        "--keep-stale",
        action="store_true",
        help="не удалять файлы отредактированных уроков (по умолчанию удаляются)",
    )
    parser.add_argument("--language", default="ru", help="язык обзора")
    args = parser.parse_args()

    targets = lessons_for(args.lessons, args.language)
    # Урок без сценария обзора пропускается молча: сценарии пишутся отдельным
    # шагом, и отсутствие — это «ещё не сгенерирован», а не поломка.
    without_script = [l for l in targets if not audio.has_script(l, args.language)]
    targets = [l for l in targets if audio.has_script(l, args.language)]
    wanted = {audio.audio_path(lesson, args.language).name for lesson in targets}
    built = skipped = 0
    started = time.time()

    for index, lesson in enumerate(targets, start=1):
        path = audio.audio_path(lesson, args.language)
        if path.exists():
            skipped += 1
            continue
        mark = time.time()
        audio.synthesize(lesson, args.language)
        built += 1
        size = path.stat().st_size / 1024
        print(
            f"[{index:3}/{len(targets)}] {lesson['id']:<24} "
            f"{size:6.0f} КБ  {time.time() - mark:5.1f} с",
            flush=True,
        )

    removed = 0
    # Устаревшее чистится только при полном прогоне: при сборке одного урока
    # остальные файлы не «лишние», их просто не просили. И только на своём языке —
    # иначе сборка английского корпуса стёрла бы весь русский.
    if not args.keep_stale and not args.lessons:
        for stale in Path(settings.audio_dir).glob(f"*.{args.language}.*.mp3"):
            if stale.name not in wanted:
                stale.unlink()
                removed += 1

    total = sum(p.stat().st_size for p in Path(settings.audio_dir).glob("*.mp3"))
    print(
        f"\nсобрано: {built}  уже было: {skipped}  удалено устаревших: {removed}  "
        f"время: {time.time() - started:.0f} с  каталог: {total / 1024 / 1024:.0f} МБ"
    )
    if without_script:
        print(
            f"без сценария обзора: {len(without_script)} — "
            "их аудио не собирается (python -m scripts.generate_audio_scripts)"
        )


if __name__ == "__main__":
    sys.exit(main())
