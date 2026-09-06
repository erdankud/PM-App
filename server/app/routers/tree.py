"""Skill tree, blocks, lessons and gate entry (spec v0.2 §12).

Availability is decided here, not in the UI. `start_gate` re-checks it on every call so
a client that shows the wrong button cannot get a learner into a gate they have not
earned (spec v0.2 §14).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app import tree_content
from app.config import settings
from app.deps import ContentLanguage, CurrentUser, DbSession
from app.schemas import (
    LessonAudioView,
    LessonSectionView,
    TermView,
    TreeSummary,
    TreesResponse,
    BlockDetailResponse,
    BlockSummary,
    ChallengeResponse,
    DomainView,
    LessonBlockView,
    LessonCompleteResponse,
    LessonResponse,
    LessonSummary,
    NodeDetail,
    NodeView,
    TierView,
    TreeResponse,
)
from app.services import audio as audio_service
from app.services import audio_jobs
from app.services import glossary as glossary_service
from app.services import tree as tree_service
from app.views import challenge_response

router = APIRouter(tags=["tree"])


def _summary(
    block: dict, progress, completed: set[str], language: str = "ru"
) -> BlockSummary:
    lessons = tree_content.lessons_for_block(block["id"], language)
    gate = tree_content.gate_for_block(block["id"])
    return BlockSummary(
        id=block["id"],
        domain_key=block["domainKey"],
        tier=block["tier"],
        title=block["title"],
        content_status=block["status"],
        status=progress.status,
        prerequisite_block_ids=list(block["prerequisiteBlockIds"]),
        node_count=len(block["nodes"]),
        lessons_total=len(lessons),
        lessons_completed=sum(1 for l in lessons if l["id"] in completed),
        gate_id=gate["id"] if gate else None,
        attempt_count=progress.attempt_count,
    )


TREE_TITLES = {
    "product": ("Продукт", "Карта навыков продакт-менеджера"),
    "system_design": ("Системы", "Как устроен продукт изнутри"),
}


@router.get("/trees", response_model=TreesResponse)
def get_trees(user: CurrentUser, db: DbSession, language: ContentLanguage) -> TreesResponse:
    """Обе карты одной грамматики — для переключателя в табе «Дерево» (спека SD §6.1)."""
    rows = tree_service.recompute(db, user.id)
    db.commit()
    summaries = []
    for kind in tree_content.kinds():
        blocks = tree_content.blocks_of(kind, language.value)
        statuses = [rows[block["id"]].status for block in blocks]
        title, subtitle = TREE_TITLES[kind]
        summaries.append(TreeSummary(
            kind=kind,
            title=title,
            subtitle=subtitle,
            blocks_total=len(blocks),
            blocks_passed=sum(1 for s in statuses if s == tree_service.PASSED),
            blocks_available=sum(
                1 for s in statuses
                if s in (tree_service.AVAILABLE, tree_service.IN_PROGRESS,
                         tree_service.GATE_READY)
            ),
        ))
    return TreesResponse(trees=summaries)


def _tree_response(kind: str, user, db, language: str = "ru") -> TreeResponse:
    content = tree_content.tree_content(kind, language)
    rows = tree_service.recompute(db, user.id)
    db.commit()
    completed = tree_service.completed_lesson_ids(db, user.id)
    return TreeResponse(
        kind=kind,
        version=content["tree"]["version"],
        source_attribution=content["tree"]["sourceAttribution"],
        tiers=[TierView(**tier) for tier in content["tiers"]],
        domains=[
            DomainView(key=d["key"], title=d["title"], order=d["order"])
            for d in content["domains"]
        ],
        blocks=[
            _summary(block, rows[block["id"]], completed, language)
            for block in content["tree"]["blocks"]
        ],
    )


@router.get("/tree", response_model=TreeResponse)
def get_tree(user: CurrentUser, db: DbSession, language: ContentLanguage) -> TreeResponse:
    """Псевдоним основного дерева: клиенты v0.2 обновляются не мгновенно."""
    return _tree_response("product", user, db, language.value)


@router.get("/tree/{kind}", response_model=TreeResponse)
def get_tree_of_kind(
    kind: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> TreeResponse:
    if kind not in tree_content.kinds():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tree_not_found"}
        )
    return _tree_response(kind, user, db, language.value)


@router.get("/blocks/{block_id}", response_model=BlockDetailResponse)
def get_block(
    block_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> BlockDetailResponse:
    block = tree_content.block(block_id, language.value)
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "block_not_found"}
        )
    # Домен и круг берутся из того дерева, которому блок принадлежит: их два.
    content = tree_content.tree_content(
        tree_content.kind_of_block(block_id), language.value
    )

    rows = tree_service.recompute(db, user.id)
    db.commit()
    progress = rows[block_id]
    completed = tree_service.completed_lesson_ids(db, user.id)
    lessons = tree_content.lessons_for_block(block_id)
    by_node: dict[str, list[dict]] = {}
    for lesson in lessons:
        by_node.setdefault(lesson["nodeId"], []).append(lesson)

    gate = tree_content.gate_for_block(block_id)
    remaining = len(lessons) - sum(1 for l in lessons if l["id"] in completed)
    if progress.status == tree_service.LOCKED:
        reason = "locked"
    elif block["status"] != "published":
        reason = "coming_soon"
    elif remaining > 0:
        reason = "lessons_remaining"
    else:
        reason = None

    domain_title = next(
        d["title"] for d in content["domains"] if d["key"] == block["domainKey"]
    )
    tier_title = next(t["title"] for t in content["tiers"] if t["tier"] == block["tier"])

    return BlockDetailResponse(
        block=_summary(block, progress, completed),
        domain_title=domain_title,
        tier_title=tier_title,
        nodes=[
            NodeDetail(
                node=NodeView(
                    id=node["id"],
                    title=node["title"],
                    key_question=node["keyQuestion"],
                    models=node["models"],
                    ai_impact=node["aiImpact"],
                    order=node["order"],
                ),
                lessons=[
                    LessonSummary(
                        id=lesson["id"],
                        title=lesson["title"],
                        estimated_minutes=lesson["estimatedMinutes"],
                        order=lesson["order"],
                        completed=lesson["id"] in completed,
                    )
                    for lesson in sorted(
                        by_node.get(node["id"], []), key=lambda item: item["order"]
                    )
                ],
            )
            for node in sorted(block["nodes"], key=lambda item: item["order"])
        ],
        gate_available=reason is None and gate is not None,
        gate_blocked_reason=reason,
        pass_threshold=tree_service.pass_threshold(gate) if gate else 0,
    )


def _term_view(term: dict, *, seen: bool = False) -> TermView:
    return TermView(
        id=term["id"],
        term=term["term"],
        term_en=term["termEn"],
        definition=term["definition"],
        block_id=term["blockId"],
        source_lesson_id=term.get("sourceLessonId"),
        related_ids=term.get("relatedIds", []),
        seen=seen,
    )


def _audio_view(lesson: dict, language: str = "ru") -> LessonAudioView:
    """Аудио предлагается только когда файл уже лежит на диске.

    Синтез 12-минутного урока занимает около полуминуты, поэтому запускать его по
    открытию экрана нельзя: человек увидит кнопку, которая не играет. Файлы
    собираются заранее (`python -m scripts.build_audio`), а урок без файла просто
    не показывает плеер.
    """
    ready = audio_service.audio_path(lesson, language).exists()
    if not ready:
        job = audio_jobs.status_of(lesson["id"], language)
        return LessonAudioView(
            available=False,
            status=job.status if job else "absent",
            can_generate=audio_jobs.generation_allowed(),
        )
    # Отпечаток сценария в адресе: путь урока постоянен, а файл за ним меняется при
    # правке текста. Без него клиент, закешировавший mp3 по адресу, продолжал бы
    # проигрывать прошлую редакцию урока.
    version = audio_service.digest(lesson, language)
    return LessonAudioView(
        available=True,
        url=f"{settings.api_prefix}/lessons/{lesson['id']}/audio?v={version}",
        duration_seconds=audio_service.duration_seconds(lesson, language),
        status="ready",
        can_generate=audio_jobs.generation_allowed(),
    )


@router.post(
    "/lessons/{lesson_id}/audio/generate",
    response_model=LessonAudioView,
    status_code=status.HTTP_202_ACCEPTED,
)
def generate_lesson_audio(
    lesson_id: str, user: CurrentUser, language: ContentLanguage
) -> LessonAudioView:
    """Запускает сборку обзора и сразу отвечает.

    Сборка занимает около минуты, поэтому ответ означает «принято», а не «готово»:
    состояние клиент дочитывает из обычного ответа урока. Такой контракт не
    изменится, если однажды за ним встанет настоящая очередь.
    """
    lesson = _lesson_or_404(lesson_id, language.value)
    if not audio_jobs.generation_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail={"code": "audio_generation_disabled"}
        )
    audio_jobs.forget(lesson_id, language.value)
    audio_jobs.start(lesson, language.value)
    return _audio_view(lesson, language.value)


@router.get("/lessons/{lesson_id}/audio")
def get_lesson_audio(
    lesson_id: str, user: CurrentUser, language: ContentLanguage
) -> FileResponse:
    """Отдаёт mp3 урока.

    `FileResponse` сам обрабатывает `Range`, а без этого перемотка в плеере на
    iOS не работает: `AVPlayer` запрашивает куски, а не файл целиком.
    """
    lesson = _lesson_or_404(lesson_id, language.value)
    path = audio_service.audio_path(lesson, language.value)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "audio_not_built"}
        )
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=f"{lesson_id}.{language.value}.mp3",
        # Имя файла содержит хеш сценария, поэтому старый ответ никогда не окажется
        # аудио изменённого урока — кэшировать можно надолго.
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )


def _lesson_or_404(lesson_id: str, language: str = "ru") -> dict:
    lesson = tree_content.lesson(lesson_id, language)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "lesson_not_found"}
        )
    return lesson


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def get_lesson(
    lesson_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> LessonResponse:
    lesson = _lesson_or_404(lesson_id, language.value)
    block = tree_content.block(lesson["blockId"], language.value)
    node = next(n for n in block["nodes"] if n["id"] == lesson["nodeId"])

    ordered = tree_content.lessons_for_block(lesson["blockId"], language.value)
    index = next(i for i, item in enumerate(ordered) if item["id"] == lesson_id)
    next_id = ordered[index + 1]["id"] if index + 1 < len(ordered) else None

    completed = tree_service.completed_lesson_ids(db, user.id)
    # Термины урока считаются встреченными: отметка в глоссарии ставится сама.
    if lesson.get("termIds"):
        glossary_service.mark_seen(db, user.id, lesson["termIds"])
        db.commit()
    return LessonResponse(
        id=lesson["id"],
        node_id=lesson["nodeId"],
        block_id=lesson["blockId"],
        node_title=node["title"],
        title=lesson["title"],
        estimated_minutes=lesson["estimatedMinutes"],
        key_takeaway=lesson["keyTakeaway"],
        check_question=lesson.get("checkQuestion"),
        blocks=[LessonBlockView(**item) for item in lesson.get("blocks", [])],
        sections=[
            LessonSectionView(
                kind=section["kind"],
                blocks=[LessonBlockView(**item) for item in section["blocks"]],
            )
            for section in lesson.get("sections", [])
        ],
        terms=[
            _term_view(term, seen=True)
            for term in (
                tree_content.glossary_term(t, language.value)
                for t in lesson.get("termIds", [])
            )
            if term is not None
        ],
        diagrams=[
            glossary_service.diagram_view(diagram, language.value)
            for diagram in (
                tree_content.diagram(d, language.value)
                for d in lesson.get("diagramIds", [])
            )
            if diagram is not None
        ],
        exercise_id=lesson.get("exerciseId")
        or (tree_content.exercise_for_node(lesson["nodeId"]) or {}).get("id"),
        cross_refs=lesson.get("crossRefs", []),
        audio=_audio_view(lesson, language.value),
        completed=lesson_id in completed,
        next_lesson_id=next_id,
    )


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompleteResponse)
def complete_lesson(
    lesson_id: str, user: CurrentUser, db: DbSession
) -> LessonCompleteResponse:
    lesson = _lesson_or_404(lesson_id)
    block_id = lesson["blockId"]

    progress = tree_service.block_progress(db, user.id, block_id)
    if progress.status == tree_service.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "block_locked"}
        )

    _, awarded = tree_service.complete_lesson(db, user.id, lesson_id)
    rows = tree_service.recompute(db, user.id)
    db.commit()

    completed = tree_service.completed_lesson_ids(db, user.id)
    lessons = tree_content.lessons_for_block(block_id)
    done = sum(1 for item in lessons if item["id"] in completed)
    return LessonCompleteResponse(
        lesson_id=lesson_id,
        xp_awarded=awarded,
        block_status=rows[block_id].status,
        lessons_completed=done,
        lessons_total=len(lessons),
        gate_available=rows[block_id].status == tree_service.GATE_READY,
    )


@router.post("/gates/{gate_id}/start", response_model=ChallengeResponse)
def start_gate(
    gate_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> ChallengeResponse:
    try:
        attempt = tree_service.start_gate(db, user.id, gate_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "gate_not_found"}
        ) from exc
    except tree_service.BlockNotReady as exc:
        # The client should not have offered this. Refusing here is the guarantee.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "block_not_ready", "status": str(exc)},
        ) from exc

    db.commit()
    return challenge_response(db, attempt, language)
