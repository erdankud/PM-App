# -*- coding: utf-8 -*-
"""Ручная сборка аудиообзора по одному уроку.

Авторский инструмент: открыл урок — нажал «Сгенерировать» — послушал — если не
понравилось, перегенерировал. В обычной сборке это делает скрипт по всему корпусу,
но вычитывать корпус удобнее по одному уроку и сразу на слух.

Задача идёт в фоне и занимает около минуты: диалог пишет провайдер, затем идёт
синтез. Держать на это HTTP-запрос нельзя, поэтому запуск отвечает сразу, а
состояние клиент читает из обычного ответа урока.

Реестр задач — в памяти процесса. Для авторского инструмента этого достаточно:
перезапуск сервера теряет знание о незавершённой задаче, но не результат — он уже
на диске. Когда кнопку понадобится открыть всем, сюда встанет очередь и таблица
задач, а контракт эндпоинта не изменится: он и сейчас отвечает «принято», а не
«готово».
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.config import settings
from app.services import audio, audio_script

logger = logging.getLogger("pmcoach")


@dataclass
class Job:
    lesson_id: str
    status: str = "generating"  # generating | ready | failed
    detail: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def generation_allowed() -> bool:
    """Кнопка существует только там, где ей место.

    В релизной сборке генерация по нажатию означала бы поход к провайдеру на
    каждого пользователя за одинаковым результатом, а сценарий лёг бы на диск,
    который живёт до перезапуска, вместо репозитория.
    """
    return settings.allow_audio_generation


def status_of(lesson_id: str) -> Job | None:
    with _lock:
        return _jobs.get(lesson_id)


def _run(lesson: dict) -> None:
    lesson_id = lesson["id"]
    try:
        turns, provider, model = audio_script.generate(lesson)
        audio_script.write_script(lesson, turns, provider, model)
        audio.synthesize(lesson)
    except Exception as error:  # noqa: BLE001 - в статус уходит причина, наружу текст не идёт
        logger.warning("audio generation failed for %s: %s", lesson_id, error)
        with _lock:
            _jobs[lesson_id] = Job(lesson_id, "failed", str(error)[:200])
        return
    with _lock:
        _jobs[lesson_id] = Job(lesson_id, "ready")
    logger.info("audio overview built for %s", lesson_id)


def start(lesson: dict) -> Job:
    """Запускает сборку. Повторный запуск при живой задаче её не дублирует."""
    lesson_id = lesson["id"]
    with _lock:
        current = _jobs.get(lesson_id)
        if current is not None and current.status == "generating":
            return current
        job = Job(lesson_id)
        _jobs[lesson_id] = job

    threading.Thread(target=_run, args=(lesson,), daemon=True, name=f"audio-{lesson_id}").start()
    return job


def forget(lesson_id: str) -> None:
    """Убирает завершённую задачу, чтобы прошлая ошибка не липла к новой попытке."""
    with _lock:
        job = _jobs.get(lesson_id)
        if job is not None and job.status != "generating":
            del _jobs[lesson_id]
