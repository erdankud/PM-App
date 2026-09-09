"""Модуль Practice: генерация тренировок и разбор ответов.

Формирующий насквозь. Ни один ответ отсюда не меняет XP, компетенции, уровень или
доступность блока — и это правило жёстче обычного, потому что задачу здесь пишет
модель. То, что генерирует себе задание само, не должно уметь двигать счёт: иначе
достаточно попросить задачу полегче.

Ключа провайдера здесь нет и быть не может: клиент нажимает кнопку, промпт
собирает сервер (спека §13, §17).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from app import practice_catalogue
from app.deps import CurrentUser, DbSession
from app.models import PracticeSession
from app.practice_catalogue import Track
from app.schemas import (
    PracticeCanvasFieldView,
    PracticeRespondRequest,
    PracticeSessionSummary,
    PracticeSessionView,
    PracticeSessionsResponse,
    PracticeTrackView,
    PracticeTracksResponse,
)
from app.services import practice as practice_service

router = APIRouter(prefix="/practice", tags=["practice"])


def _track_or_404(track_id: str) -> Track:
    track = practice_catalogue.track(track_id)
    if track is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "practice_track_not_found"}
        )
    return track


def _live_or_409(track: Track) -> Track:
    if not track.live:
        # 409, а не 404: направление существует и видно на экране, просто ещё не
        # открыто. Разница важна клиенту — плитка остаётся, кнопка нет.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "practice_track_not_ready"},
        )
    return track


def _session_or_404(db: DbSession, user_id: str, session_id: str) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    # Чужая тренировка — «нет такой», а не «нельзя»: наличие чужой записи не
    # подтверждается.
    if session is None or session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "practice_session_not_found"},
        )
    return session


def _view(session: PracticeSession) -> PracticeSessionView:
    return PracticeSessionView(
        id=session.id,
        track=session.track,
        status=session.status,
        brief=session.brief,
        answers=session.answers or {},
        asked=session.asked or [],
        feedback=session.feedback,
        elapsed_seconds=session.elapsed_seconds,
        created_at=session.created_at.isoformat(),
        answered_at=session.answered_at.isoformat() if session.answered_at else None,
    )


def _summary(session: PracticeSession) -> PracticeSessionSummary:
    brief = session.brief or {}
    feedback = session.feedback or {}
    return PracticeSessionSummary(
        id=session.id,
        track=session.track,
        status=session.status,
        title=brief.get("title", ""),
        company=brief.get("company", ""),
        bar=feedback.get("bar"),
        created_at=session.created_at.isoformat(),
        answered_at=session.answered_at.isoformat() if session.answered_at else None,
    )


def _unavailable(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": code}
    )


@router.get("/tracks", response_model=PracticeTracksResponse)
def list_tracks(user: CurrentUser, db: DbSession) -> PracticeTracksResponse:
    counts: dict[str, list[int]] = {}
    for session in practice_service.sessions_for(db, user.id):
        row = counts.setdefault(session.track, [0, 0])
        row[0] += 1
        if session.status == "answered":
            row[1] += 1

    tracks = []
    for track in practice_catalogue.TRACKS:
        total, answered = counts.get(track.id, [0, 0])
        tracks.append(
            PracticeTrackView(
                id=track.id,
                title=track.title,
                blurb=track.blurb,
                tests=track.tests,
                format=track.format,
                live=track.live,
                target_minutes=track.target_minutes,
                canvas=[
                    PracticeCanvasFieldView(
                        id=item.id,
                        label=item.label,
                        hint=item.hint,
                        min_chars=item.min_chars,
                        rows=item.rows,
                    )
                    for item in track.canvas
                ],
                sessions_total=total,
                sessions_answered=answered,
            )
        )
    return PracticeTracksResponse(tracks=tracks)


@router.post(
    "/tracks/{track_id}/sessions",
    response_model=PracticeSessionView,
    status_code=status.HTTP_201_CREATED,
)
def create_session(track_id: str, user: CurrentUser, db: DbSession) -> PracticeSessionView:
    """Кнопка «следующая задача».

    Банка вопросов нет намеренно: пятьдесят заготовленных задач кончаются, а
    заготовленную задачу второй человек уже видел в чужом разборе. Здесь задача
    пишется на нажатие, а от повтора защищает список заголовков, которые этот
    человек в этом направлении уже видел.
    """
    track = _live_or_409(_track_or_404(track_id))
    try:
        session = practice_service.generate(db, user.id, track)
    except practice_service.PracticeRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": exc.code}
        ) from exc
    except practice_service.PracticeUnavailable as exc:
        raise _unavailable("practice_generation_failed") from exc
    return _view(session)


@router.get("/sessions", response_model=PracticeSessionsResponse)
def list_sessions(
    user: CurrentUser,
    db: DbSession,
    track: str | None = Query(default=None),
) -> PracticeSessionsResponse:
    rows = practice_service.sessions_for(db, user.id, track)
    return PracticeSessionsResponse(sessions=[_summary(row) for row in rows])


@router.get("/sessions/{session_id}", response_model=PracticeSessionView)
def get_session(session_id: str, user: CurrentUser, db: DbSession) -> PracticeSessionView:
    return _view(_session_or_404(db, user.id, session_id))


@router.post("/sessions/{session_id}/response", response_model=PracticeSessionView)
def respond(
    session_id: str,
    payload: PracticeRespondRequest,
    user: CurrentUser,
    db: DbSession,
) -> PracticeSessionView:
    session = _session_or_404(db, user.id, session_id)
    track = _live_or_409(_track_or_404(session.track))
    if session.status == "answered":
        # Переписать разбор нельзя: сохранённая тренировка — это запись того, что
        # человек написал тогда, и её ценность в том, что она не меняется.
        # Следующая попытка — новая задача.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "practice_already_answered"},
        )
    if not any((payload.answers.get(item.id) or "").strip() for item in track.canvas):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "practice_answer_empty"},
        )
    try:
        session = practice_service.respond(
            db,
            session,
            track,
            answers=payload.answers,
            asked=payload.asked,
            elapsed_seconds=payload.elapsed_seconds,
        )
    except practice_service.PracticeRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"code": exc.code}
        ) from exc
    except practice_service.PracticeUnavailable as exc:
        raise _unavailable("practice_feedback_failed") from exc
    return _view(session)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_session(session_id: str, user: CurrentUser, db: DbSession) -> Response:
    """Убрать сохранённую тренировку.

    Сохранённое здесь — это черновики мышления, и человек имеет право их
    выбросить, не объясняя причин.
    """
    session = _session_or_404(db, user.id, session_id)
    db.delete(session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
