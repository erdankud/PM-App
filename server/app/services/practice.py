"""Оркестрация модуля Practice: генерация задачи и разбор ответа.

Обе операции синхронные, в отличие от разбора гейта, который идёт через очередь.
Причина не в скорости, а в том, что это разные события. Гейт человек сдаёт и
уходит — разбор догоняет его письмом на экране прогресса. Тренировку он ждёт: он
нажал «сгенерировать» и смотрит на пустой экран, и очередь здесь означала бы
опрос сервера ради того же самого ожидания, только с лишним состоянием.

Модуль формирующий: XP не начисляется, компетенции не двигаются, доступность
блоков не меняется. Нигде ниже нет вызова `skills` или `scoring` — и это
намеренно, а не потому, что до них не дошли руки.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import practice_catalogue
from app.ai.base import (
    PRACTICE_PROMPT_VERSION,
    EvaluationRequest,
    ProviderError,
    QuotaExhausted,
)
from app.ai.practice_prompt import build_brief_prompt, build_feedback_prompt
from app.ai.practice_validation import InvalidPracticeOutput, parse_brief, parse_feedback
from app.ai.registry import get_provider
from app.config import settings
from app.models import PracticeSession, new_id, utcnow
from app.practice_catalogue import Track

logger = logging.getLogger("pmcoach.practice")

# Заголовки прошлых задач, которые уходят в запрос как «не повторяй это».
RECENT_TITLES = 12


class PracticeRateLimited(RuntimeError):
    def __init__(self, code: str = "daily_practice_limit_reached") -> None:
        super().__init__(code)
        self.code = code


class PracticeUnavailable(RuntimeError):
    """Провайдер не смог отдать пригодный ответ за отведённые попытки."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def check_daily_quota(db: Session, user_id: str) -> None:
    """Обе операции — обращение к провайдеру, поэтому и считаются вместе.

    Считаются сессии за сутки: одна тренировка это генерация плюс разбор, то есть
    два вызова, и лимит проще держать честным, считая тренировки, а не запросы.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    count = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == user_id, PracticeSession.created_at >= since)
        .count()
    )
    if count >= settings.practice_sessions_per_user_per_day:
        raise PracticeRateLimited()


def _call(request: EvaluationRequest, parse) -> tuple[dict, str]:
    """Вызов провайдера с повторами. Возвращает (разобранный ответ, id модели).

    Невалидный вывод здесь — повод повторить, а не показать: человек не должен
    видеть ни обрезанный JSON, ни задачу без вопроса. Ошибка провайдера наружу
    уходит одним кодом, без текста от провайдера.
    """
    provider = get_provider()
    last_code = "provider_unknown_error"
    for attempt_index in range(settings.evaluator_max_attempts):
        try:
            response = provider.evaluate(request)
            return parse(response.raw_text), response.model_id
        except QuotaExhausted as exc:
            logger.warning("practice: provider daily quota exhausted: %s", exc)
            raise PracticeUnavailable("provider_quota_exhausted") from exc
        except ProviderError as exc:
            last_code = exc.code
            logger.warning("practice: provider error (%s): %s", exc.code, exc)
            if not exc.retryable:
                break
        except InvalidPracticeOutput as exc:
            last_code = f"invalid_output_{exc.code}"
            logger.warning("practice: provider returned invalid output: %s", exc.code)
        if attempt_index < settings.evaluator_max_attempts - 1:
            time.sleep(settings.evaluator_backoff_seconds * (2**attempt_index))
    raise PracticeUnavailable(last_code)


def recent_titles(db: Session, user_id: str, track_id: str) -> list[str]:
    rows = (
        db.query(PracticeSession.brief)
        .filter(PracticeSession.user_id == user_id, PracticeSession.track == track_id)
        .order_by(PracticeSession.created_at.desc())
        .limit(RECENT_TITLES)
        .all()
    )
    titles = []
    for (brief,) in rows:
        title = (brief or {}).get("title")
        if title:
            titles.append(title)
    return titles


def sessions_for(db: Session, user_id: str, track_id: str | None = None) -> list[PracticeSession]:
    query = db.query(PracticeSession).filter(PracticeSession.user_id == user_id)
    if track_id:
        query = query.filter(PracticeSession.track == track_id)
    return query.order_by(PracticeSession.created_at.desc()).all()


def generate(db: Session, user_id: str, track: Track) -> PracticeSession:
    check_daily_quota(db, user_id)
    previous = recent_titles(db, user_id, track.id)
    system_prompt, user_prompt = build_brief_prompt(track, avoid_titles=previous)
    request = EvaluationRequest(
        scenario_id=f"practice:{track.id}",
        scenario_version=1,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context={
            "practice": {
                "track": track.id,
                "stage": "brief",
                # Заглушке нужен счётчик, чтобы кнопка «следующая» отдавала
                # следующую, а не ту же самую.
                "sequence": len(previous),
            }
        },
        # Задача каждый раз новая — иначе кнопка бессмысленна.
        temperature=1.0,
        max_output_tokens=2000,
    )
    brief, model_id = _call(request, lambda text: parse_brief(text, track))

    session = PracticeSession(
        id=new_id(),
        user_id=user_id,
        track=track.id,
        status="open",
        brief=brief,
        answers={},
        asked=[],
        brief_model_id=model_id,
        prompt_version=PRACTICE_PROMPT_VERSION,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def respond(
    db: Session,
    session: PracticeSession,
    track: Track,
    *,
    answers: dict[str, str],
    asked: list[str],
    elapsed_seconds: int | None,
) -> PracticeSession:
    check_daily_quota(db, session.user_id)
    # Поля берутся по канве, а не по тому, что прислал клиент: лишний ключ в
    # запросе не должен попадать в промпт.
    cleaned = {
        item.id: (answers.get(item.id) or "").strip()[:4000] for item in track.canvas
    }
    known = {entry["question"] for entry in session.brief.get("clarifiers", [])}
    kept_asked = [question for question in asked if question in known]

    system_prompt, user_prompt = build_feedback_prompt(
        track,
        brief=session.brief,
        answers=cleaned,
        asked=kept_asked,
        elapsed_seconds=elapsed_seconds,
    )
    request = EvaluationRequest(
        scenario_id=f"practice:{track.id}:{session.id}",
        scenario_version=1,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context={
            "practice": {"track": track.id, "stage": "feedback", "answers": cleaned}
        },
    )
    feedback, model_id = _call(request, lambda text: parse_feedback(text, track))

    session.answers = cleaned
    session.asked = kept_asked
    session.feedback = feedback
    session.feedback_model_id = model_id
    session.elapsed_seconds = elapsed_seconds
    session.status = "answered"
    session.answered_at = utcnow()
    db.commit()
    db.refresh(session)
    return session


def track_or_none(track_id: str) -> Track | None:
    return practice_catalogue.track(track_id)
