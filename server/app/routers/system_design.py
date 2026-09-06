"""Упражнения, глоссарий и схемы домена System Design (спека SD §5).

Упражнения формирующие: они не входят в `final_score`, не дают XP и не влияют на
доступность гейта. Поэтому эталонное рассуждение отдаётся всегда — даже на пустой
ответ, потому что человек, не знающий, как подступиться, должен увидеть разбор.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app import tree_content
from app.deps import ContentLanguage, CurrentUser, DbSession
from app.models import ExerciseAttempt, utcnow
from app.schemas import (
    DiagramView,
    ExerciseInputResult,
    ExerciseInputView,
    ExerciseResponse,
    ExerciseSubmitRequest,
    ExerciseSubmitResponse,
    GlossaryResponse,
    LessonBlockView,
    TermView,
)
from app.services import glossary as glossary_service

router = APIRouter(tags=["system-design"])


def _exercise_or_404(exercise_id: str, language: str = "ru") -> dict:
    exercise = tree_content.exercise(exercise_id, language)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "exercise_not_found"}
        )
    return exercise


def _attempt(db: DbSession, user_id: str, exercise_id: str) -> ExerciseAttempt | None:
    return (
        db.query(ExerciseAttempt)
        .filter(
            ExerciseAttempt.user_id == user_id,
            ExerciseAttempt.exercise_id == exercise_id,
        )
        .one_or_none()
    )


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> ExerciseResponse:
    exercise = _exercise_or_404(exercise_id, language.value)
    previous = _attempt(db, user.id, exercise_id)
    return ExerciseResponse(
        id=exercise["id"],
        node_id=exercise["nodeId"],
        block_id=exercise["blockId"],
        type=exercise["type"],
        title=exercise["title"],
        estimated_minutes=exercise["estimatedMinutes"],
        prompt_blocks=[LessonBlockView(**block) for block in exercise["promptBlocks"]],
        inputs=[ExerciseInputView(**item) for item in exercise["inputs"]],
        submitted_values=(previous.submitted_values or {}) if previous else {},
        diagrams=[
            glossary_service.diagram_view(diagram, language.value)
            for diagram in (
                tree_content.diagram(block["diagramId"], language.value)
                for block in exercise["promptBlocks"]
                if block["type"] == "diagram_ref"
            )
            if diagram is not None
        ],
    )


def _check(exercise: dict, values: dict[str, str]) -> list[ExerciseInputResult]:
    """Проверка по порядку величины, а не по точному совпадению (спека SD §5.1)."""
    results: list[ExerciseInputResult] = []
    for rule in exercise["acceptance"]:
        raw = values.get(rule["inputId"])
        within: bool | None = None
        if raw not in (None, ""):
            if "expected" in rule:
                within = str(raw).strip().lower() == str(rule["expected"]).strip().lower()
            else:
                try:
                    number = float(str(raw).replace(",", ".").replace(" ", ""))
                except ValueError:
                    within = False
                else:
                    low = rule.get("min", float("-inf"))
                    high = rule.get("max", float("inf"))
                    within = low <= number <= high
        hint = None
        if "min" in rule or "max" in rule:
            hint = f"{rule.get('min', '')}–{rule.get('max', '')}".strip("–")
        elif "expected" in rule:
            hint = str(rule["expected"])
        results.append(
            ExerciseInputResult(input_id=rule["inputId"], within_range=within, expected_hint=hint)
        )
    return results


@router.post("/exercises/{exercise_id}/submit", response_model=ExerciseSubmitResponse)
def submit_exercise(
    exercise_id: str,
    payload: ExerciseSubmitRequest,
    user: CurrentUser,
    db: DbSession,
    language: ContentLanguage,
) -> ExerciseSubmitResponse:
    # Эталон разбора приходит на языке читателя; приёмка сверяется с ним же, иначе
    # выбранный вариант перестал бы совпадать с эталоном при смене языка.
    exercise = _exercise_or_404(exercise_id, language.value)
    attempt = _attempt(db, user.id, exercise_id)
    if attempt is None:
        attempt = ExerciseAttempt(user_id=user.id, exercise_id=exercise_id)
        db.add(attempt)
    attempt.submitted_values = dict(payload.values)
    attempt.viewed_reference_at = attempt.viewed_reference_at or utcnow()
    db.commit()

    return ExerciseSubmitResponse(
        exercise_id=exercise_id,
        results=_check(exercise, payload.values),
        reference_reasoning_blocks=[
            LessonBlockView(**block) for block in exercise["referenceReasoningBlocks"]
        ],
    )


@router.get("/glossary", response_model=GlossaryResponse)
def get_glossary(
    user: CurrentUser,
    db: DbSession,
    language: ContentLanguage,
    block_id: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=64),
) -> GlossaryResponse:
    """Весь глоссарий разом: около 80 КБ, клиент кэширует его целиком."""
    seen = glossary_service.seen_term_ids(db, user.id)
    needle = (q or "").strip().lower()
    terms = []
    for term in tree_content.glossary_terms(language=language.value):
        if block_id and term["blockId"] != block_id:
            continue
        if needle and needle not in term["term"].lower() and needle not in term["termEn"].lower():
            continue
        terms.append(
            TermView(
                id=term["id"],
                term=term["term"],
                term_en=term["termEn"],
                definition=term["definition"],
                block_id=term["blockId"],
                source_lesson_id=term.get("sourceLessonId"),
                related_ids=term.get("relatedIds", []),
                seen=term["id"] in seen,
            )
        )
    return GlossaryResponse(version=1, terms=terms)


@router.get("/glossary/{term_id}", response_model=TermView)
def get_term(
    term_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> TermView:
    term = tree_content.glossary_term(term_id, language.value)
    if term is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "term_not_found"}
        )
    seen = glossary_service.seen_term_ids(db, user.id)
    return TermView(
        id=term["id"],
        term=term["term"],
        term_en=term["termEn"],
        definition=term["definition"],
        block_id=term["blockId"],
        source_lesson_id=term.get("sourceLessonId"),
        related_ids=term.get("relatedIds", []),
        seen=term_id in seen,
    )


@router.get("/diagrams/{diagram_id}", response_model=DiagramView)
def get_diagram(
    diagram_id: str, user: CurrentUser, language: ContentLanguage
) -> DiagramView:
    """Для полноэкранного просмотра из глоссария; в уроке схемы едут вместе с ним."""
    diagram = tree_content.diagram(diagram_id, language.value)
    if diagram is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "diagram_not_found"}
        )
    return glossary_service.diagram_view(diagram, language.value)
