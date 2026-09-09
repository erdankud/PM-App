"""API request/response contracts (spec §15).

camelCase on the wire, snake_case in Python. The iOS client mirrors these exactly.
Note what is deliberately absent from client-facing payloads: the authored rubric,
option consequence text before submission, and any AI provider or prompt metadata.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

try:  # pragma: no cover - зависит от того, установлен ли email-validator
    from pydantic import EmailStr
except ImportError:  # pragma: no cover
    EmailStr = str  # type: ignore[misc, assignment]


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(word.capitalize() for word in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


# --- Auth -------------------------------------------------------------------


class AppleSignInRequest(ApiModel):
    identity_token: str = Field(min_length=16, max_length=4096)
    timezone: str | None = Field(default=None, max_length=64)


class GoogleSignInRequest(ApiModel):
    id_token: str = Field(min_length=16, max_length=4096)
    timezone: str | None = Field(default=None, max_length=64)


class EmailPasswordRequest(ApiModel):
    """Регистрация и вход отличаются только тем, что делает сервер, — не формой."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)


class AuthMethodsResponse(ApiModel):
    """Что клиент имеет право показать на экране входа.

    Решает сервер: кнопка Google без настроенного Client ID — это обещание, которого
    он не сможет выполнить.
    """

    password: bool
    google: bool
    apple: bool
    developer: bool
    google_client_id: str | None = None


class DevSignInRequest(ApiModel):
    device_id: str = Field(min_length=8, max_length=128)
    timezone: str | None = Field(default=None, max_length=64)


class RefreshRequest(ApiModel):
    refresh_token: str = Field(min_length=16, max_length=512)


class SignOutRequest(ApiModel):
    refresh_token: str | None = Field(default=None, max_length=512)


# --- Profile ----------------------------------------------------------------


class SkillView(ApiModel):
    key: str
    label: str
    score: int
    trend: Literal["up", "down", "steady"] = "steady"


class MeResponse(ApiModel):
    user_id: str
    onboarding_status: str
    target_role: str | None
    timezone: str
    language: str
    current_level: str | None
    level: int
    total_xp: int
    xp_for_next_level: int | None
    streak_count: int
    entitlement: str
    focus_skills: list[str]
    skills: list[SkillView]


class AuthResponse(ApiModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: MeResponse


class ProfileUpdateRequest(ApiModel):
    # Only a highlight filter over the map in this version (spec v0.2 §7).
    target_role: str | None = Field(default=None, max_length=48)
    timezone: str | None = Field(default=None, max_length=64)
    language: Literal["en", "ru"] | None = None
    complete_onboarding: bool | None = None


# --- Today / challenge ------------------------------------------------------

ChallengeState = Literal[
    "not_started", "in_progress", "submitted", "awaiting_feedback", "complete", "feedback_failed"
]


class TodayAssignment(ApiModel):
    assignment_id: str
    local_date: str
    scenario_id: str
    title: str
    summary: str
    estimated_minutes: int
    level: str
    primary_skill: str
    primary_skill_label: str
    context_label: str
    state: ChallengeState
    attempt_id: str | None
    score: int | None


class TodayResponse(ApiModel):
    local_date: str
    assignment: TodayAssignment
    upcoming: list[PathPreviewDay]
    level: int
    total_xp: int
    streak_count: int
    focus_skills: list[SkillView]


class BriefView(ApiModel):
    role: str
    company: str
    context: str
    objective: str
    constraints: str
    task: str
    what_good_looks_like: str


class EvidenceCardView(ApiModel):
    id: str
    title: str
    type: str
    order: int
    content: str


class DecisionOptionView(ApiModel):
    id: str
    label: str
    description: str


class ScenarioView(ApiModel):
    id: str
    version: int
    title: str
    summary: str
    estimated_minutes: int
    level: str
    primary_skill: str
    primary_skill_label: str
    tags: list[str]
    brief: BriefView
    evidence_cards: list[EvidenceCardView]
    decision_prompt: str
    decision_options: list[DecisionOptionView]


class AttemptView(ApiModel):
    attempt_id: str
    status: str
    selected_option_id: str | None
    rationale: str | None
    reviewed_evidence_ids: list[str]
    rationale_min: int = 30
    rationale_max: int = 600


class ChallengeResponse(ApiModel):
    gate_id: str
    block_id: str
    block_title: str
    attempt_index: int
    pass_threshold: int
    state: ChallengeState
    scenario: ScenarioView
    attempt: AttemptView


class DraftRequest(ApiModel):
    selected_option_id: str | None = Field(default=None, max_length=64)
    rationale: str | None = Field(default=None, max_length=600)
    client_updated_at: str | None = None


class DraftResponse(ApiModel):
    attempt_id: str
    status: str
    selected_option_id: str | None
    rationale_length: int
    saved_at: str


class EvidenceRequest(ApiModel):
    evidence_card_id: str = Field(max_length=64)


class EvidenceResponse(ApiModel):
    attempt_id: str
    reviewed_evidence_ids: list[str]
    reviewed_count: int
    total_count: int


class SubmitRequest(ApiModel):
    selected_option_id: str = Field(max_length=64)
    rationale: str = Field(min_length=1, max_length=600)

    @field_validator("rationale")
    @classmethod
    def _min_meaningful_length(cls, value: str) -> str:
        if len(value.strip()) < 30:
            raise ValueError("rationale must be at least 30 non-whitespace characters")
        return value


class ConsequenceView(ApiModel):
    option_id: str
    option_label: str
    text: str


class SubmitResponse(ApiModel):
    attempt_id: str
    status: str
    consequence: ConsequenceView
    feedback_status: Literal["pending", "complete", "failed"]


# --- Feedback ---------------------------------------------------------------


class FeedbackPoint(ApiModel):
    title: str
    detail: str


class SkillImpact(ApiModel):
    key: str
    label: str
    delta: int
    score: int


class ScoreBreakdownView(ApiModel):
    evidence: int
    evidence_max: int
    decision: int
    decision_max: int
    rationale: int
    rationale_max: int
    communication: int
    communication_max: int


class FeedbackBody(ApiModel):
    score: int
    band: str
    breakdown: ScoreBreakdownView
    strengths: list[FeedbackPoint]
    improvements: list[FeedbackPoint]
    sharper_approach: str
    skill_impact: list[SkillImpact]
    xp_awarded: int
    needs_retry: bool


class RemediationLink(ApiModel):
    gap: str
    lesson_id: str
    lesson_title: str


class FeedbackResponse(ApiModel):
    attempt_id: str
    status: Literal["pending", "complete", "failed"]
    consequence: ConsequenceView
    feedback: FeedbackBody | None
    rating: str | None
    retry_available: bool
    scenario_title: str
    learn_takeaway_title: str | None = None
    # Gate outcome. `passed` is None while the evaluation is still pending.
    gate_id: str | None = None
    block_id: str | None = None
    block_title: str | None = None
    passed: bool | None = None
    pass_threshold: int | None = None
    attempt_index: int | None = None
    unlocked_block_ids: list[str] = []
    remediation: list[RemediationLink] = []


class RatingRequest(ApiModel):
    rating: Literal["useful", "not_useful"]


# --- Progress / history -----------------------------------------------------


class ProgressResponse(ApiModel):
    level: int
    total_xp: int
    xp_for_next_level: int | None
    blocks_passed: int
    blocks_total: int
    lessons_completed: int
    lessons_total: int
    gates_attempted: int
    skills: list[SkillView]
    footnote: str


class HistoryItem(ApiModel):
    """One gate sitting. History is by attempt now, not by calendar day."""

    attempt_id: str
    gate_id: str
    block_id: str
    block_title: str
    scenario_id: str
    title: str
    attempt_index: int
    submitted_at: str | None
    score: int | None
    passed: bool | None
    feedback_status: Literal["pending", "complete", "failed"]


class HistoryResponse(ApiModel):
    items: list[HistoryItem]
    next_offset: int | None


# --- Analytics --------------------------------------------------------------


class AnalyticsEventIn(ApiModel):
    name: str = Field(max_length=64)
    properties: dict[str, Any] = Field(default_factory=dict)
    app_version: str | None = Field(default=None, max_length=32)
    platform: str | None = Field(default=None, max_length=16)
    client_timestamp: str | None = None


class AnalyticsBatch(ApiModel):
    events: list[AnalyticsEventIn] = Field(max_length=50)


class SimpleOk(ApiModel):
    ok: bool = True


# --- Skill tree (spec v0.2 §12) ----------------------------------------------


class TierView(ApiModel):
    tier: int
    title: str
    subtitle: str


class DomainView(ApiModel):
    key: str
    title: str
    order: int


class NodeView(ApiModel):
    id: str
    title: str
    key_question: str
    models: list[str]
    ai_impact: str | None = None
    order: int


class BlockSummary(ApiModel):
    id: str
    domain_key: str
    tier: int
    title: str
    # Whether the content exists yet. Orthogonal to the learner's own progress.
    content_status: str
    # locked | available | in_progress | gate_ready | passed
    status: str
    prerequisite_block_ids: list[str]
    node_count: int
    lessons_total: int
    lessons_completed: int
    gate_id: str | None
    attempt_count: int


class TreeSummary(ApiModel):
    """Одна карта в переключателе «Продукт» / «Системы» (спека SD §6.1)."""

    kind: str
    title: str
    subtitle: str
    blocks_total: int
    blocks_passed: int
    blocks_available: int


class TreesResponse(ApiModel):
    trees: list[TreeSummary]


class TreeResponse(ApiModel):
    kind: str = "product"
    version: int
    source_attribution: str
    tiers: list[TierView]
    domains: list[DomainView]
    blocks: list[BlockSummary]


class LessonSummary(ApiModel):
    id: str
    title: str
    estimated_minutes: int
    order: int
    completed: bool


class MapNode(ApiModel):
    """Узел карты — одна карточка. Именно навык, как в исходной схеме: название,
    ключевой вопрос и модели. Уроки узла приложены, потому что карточка ведёт
    в урок, а не в блок."""

    id: str
    block_id: str
    domain_key: str
    tier: int
    order: int
    title: str
    key_question: str
    models: list[str]
    # Статус блока, которому принадлежит узел: доступность живёт на блоке.
    block_status: str
    lessons: list[LessonSummary]


class MapEdge(ApiModel):
    """Связь между узлами. Внутри блока — порядок прохождения, между блоками —
    зависимость из графа разблокировки. Ничего не выдумано."""

    source: str
    target: str
    kind: str  # sequence | prerequisite


class MapResponse(ApiModel):
    kind: str
    source_attribution: str
    tiers: list[TierView]
    domains: list[DomainView]
    nodes: list[MapNode]
    edges: list[MapEdge]


class NodeDetail(ApiModel):
    node: NodeView
    lessons: list[LessonSummary]


class BlockDetailResponse(ApiModel):
    block: BlockSummary
    domain_title: str
    tier_title: str
    nodes: list[NodeDetail]
    gate_available: bool
    gate_blocked_reason: str | None = None
    pass_threshold: int


class LessonBlockView(ApiModel):
    """One rendered element of a lesson. Shape depends on `type`."""

    type: str
    text: str | None = None
    title: str | None = None
    subtitle: str | None = None
    tone: str | None = None
    ordered: bool | None = None
    items: list[str] | None = None
    header: list[str] | None = None
    rows: list[list[str]] | None = None
    diagram_id: str | None = None


class TermView(ApiModel):
    id: str
    term: str
    term_en: str
    definition: str
    block_id: str
    source_lesson_id: str | None = None
    related_ids: list[str] = []
    seen: bool = False


class DiagramNodeView(ApiModel):
    id: str
    type: str
    label: str


class DiagramEdgeView(ApiModel):
    from_: str = Field(alias="from")
    to: str
    type: str
    label: str | None = None


class DiagramView(ApiModel):
    id: str
    title: str
    nodes: list[DiagramNodeView]
    edges: list[DiagramEdgeView]
    text_description: str


class LessonSectionView(ApiModel):
    kind: str
    blocks: list[LessonBlockView]


class LessonAudioView(ApiModel):
    """Аудиообзор урока. Его может не быть — это не ошибка, а отсутствие файла."""

    available: bool
    url: str | None = None
    duration_seconds: int | None = None
    # absent — обзора нет; generating — собирается; ready — готов; failed — не вышло.
    status: str = "absent"
    # Кнопка сборки есть только в дев-сборке; клиент не решает это сам.
    can_generate: bool = False


class LessonResponse(ApiModel):
    id: str
    node_id: str
    block_id: str
    node_title: str
    title: str
    estimated_minutes: int
    key_takeaway: str
    check_question: str | None = None
    blocks: list[LessonBlockView] = []
    sections: list[LessonSectionView] = []
    terms: list[TermView] = []
    # Схемы едут вместе с уроком: их одна-две, и лишний проход по мобильной сети
    # дороже размера структуры (спека SD §5.2).
    diagrams: list[DiagramView] = []
    exercise_id: str | None = None
    cross_refs: list[str] = []
    audio: LessonAudioView | None = None
    completed: bool
    next_lesson_id: str | None = None


class LessonCompleteResponse(ApiModel):
    lesson_id: str
    xp_awarded: int
    block_status: str
    lessons_completed: int
    lessons_total: int
    gate_available: bool




# --- System Design: упражнения и глоссарий -----------------------------------


class ExerciseInputView(ApiModel):
    id: str
    label: str
    unit: str | None = None
    type: str
    choices: list[str] = []


class ExerciseResponse(ApiModel):
    id: str
    node_id: str
    block_id: str
    type: str
    title: str
    estimated_minutes: int
    prompt_blocks: list[LessonBlockView]
    inputs: list[ExerciseInputView]
    submitted_values: dict[str, str] = {}
    diagrams: list[DiagramView] = []


class ExerciseInputResult(ApiModel):
    input_id: str
    within_range: bool | None = None
    expected_hint: str | None = None


class ExerciseSubmitRequest(ApiModel):
    values: dict[str, str] = {}


class ExerciseSubmitResponse(ApiModel):
    exercise_id: str
    results: list[ExerciseInputResult]
    # Эталон приходит всегда, даже на пустой ответ: упражнение формирующее,
    # и человек, не знающий, как подступиться, должен увидеть разбор (спека SD §5.2).
    reference_reasoning_blocks: list[LessonBlockView]


class GlossaryResponse(ApiModel):
    version: int
    terms: list[TermView]


# --- Practice ---------------------------------------------------------------


class PracticeCanvasFieldView(ApiModel):
    id: str
    label: str
    hint: str
    min_chars: int
    rows: int


class PracticeTrackView(ApiModel):
    """Направление тренировки.

    Тексты приходят по-английски при любом языке интерфейса и не переводятся:
    Practice готовит к собеседованию, которое проходит на английском (см.
    `app/practice_catalogue.py`).
    """

    id: str
    title: str
    blurb: str
    tests: str
    format: str
    live: bool
    target_minutes: int
    canvas: list[PracticeCanvasFieldView] = Field(default_factory=list)
    sessions_total: int = 0
    sessions_answered: int = 0


class PracticeTracksResponse(ApiModel):
    tracks: list[PracticeTrackView]


class PracticeClarifierView(ApiModel):
    question: str
    answer: str


class PracticeBriefView(ApiModel):
    title: str
    company: str
    kind: str
    context: str
    prompt: str
    constraints: list[str] = Field(default_factory=list)
    clarifiers: list[PracticeClarifierView] = Field(default_factory=list)


class PracticeFieldFeedbackView(ApiModel):
    id: str
    score: int
    note: str


class PracticeFeedbackView(ApiModel):
    headline: str
    bar: str
    fields: list[PracticeFieldFeedbackView] = Field(default_factory=list)
    strengths: list[dict[str, str]] = Field(default_factory=list)
    improvements: list[dict[str, str]] = Field(default_factory=list)
    missed_question: str
    sharper_approach: str


class PracticeSessionView(ApiModel):
    """Сохранённая тренировка целиком: задача, ответ, разбор.

    Ни модели, ни версии промпта здесь нет — клиент о них не знает и знать не
    должен (спека §15).
    """

    id: str
    track: str
    status: Literal["open", "answered"]
    brief: PracticeBriefView
    answers: dict[str, str] = Field(default_factory=dict)
    asked: list[str] = Field(default_factory=list)
    feedback: PracticeFeedbackView | None = None
    elapsed_seconds: int | None = None
    created_at: str
    answered_at: str | None = None


class PracticeSessionSummary(ApiModel):
    id: str
    track: str
    status: Literal["open", "answered"]
    title: str
    company: str
    bar: str | None = None
    created_at: str
    answered_at: str | None = None


class PracticeSessionsResponse(ApiModel):
    sessions: list[PracticeSessionSummary]


class PracticeRespondRequest(ApiModel):
    answers: dict[str, str]
    asked: list[str] = Field(default_factory=list)
    # Сколько человек просидел над задачей. Не таймер и не ограничение: разбор
    # знает про темп, потому что тонкий ответ за три минуты и тонкий ответ за
    # полчаса — разные проблемы.
    elapsed_seconds: int | None = Field(default=None, ge=0, le=60 * 60 * 8)
