"""API request/response contracts (spec §15).

camelCase on the wire, snake_case in Python. The iOS client mirrors these exactly.
Note what is deliberately absent from client-facing payloads: the authored rubric,
option consequence text before submission, and any AI provider or prompt metadata.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(word.capitalize() for word in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


# --- Auth -------------------------------------------------------------------


class AppleSignInRequest(ApiModel):
    identity_token: str = Field(min_length=16, max_length=4096)
    timezone: str | None = Field(default=None, max_length=64)


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
    goal: str | None
    timezone: str
    starting_level: str | None
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
    goal: Literal["break_into_pm", "grow_in_first_role", "practise_product_thinking"] | None = None
    timezone: str | None = Field(default=None, max_length=64)
    complete_onboarding: bool | None = None


# --- Assessment -------------------------------------------------------------


class AssessmentOption(ApiModel):
    id: str
    label: str


class AssessmentItem(ApiModel):
    id: str
    index: int
    total: int
    prompt: str
    context: str
    question: str
    options: list[AssessmentOption]


class AssessmentStateResponse(ApiModel):
    notice: str
    total_items: int
    completed_items: int
    completed: bool
    next_item: AssessmentItem | None


class AssessmentAnswerRequest(ApiModel):
    item_id: str = Field(max_length=64)
    choice_id: str = Field(max_length=64)
    rationale: str | None = Field(default=None, max_length=600)


class PathPreviewDay(ApiModel):
    local_date: str
    day_index: int
    scenario_id: str
    title: str
    primary_skill: str
    primary_skill_label: str
    level: str
    estimated_minutes: int
    is_today: bool


class AssessmentResultResponse(ApiModel):
    starting_level: str
    focus_skills: list[SkillView]
    skills: list[SkillView]
    path: list[PathPreviewDay]
    disclaimer: str


class AssessmentAnswerResponse(ApiModel):
    completed: bool
    next_item: AssessmentItem | None
    result: AssessmentResultResponse | None


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
    assignment_id: str
    local_date: str
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


class FeedbackResponse(ApiModel):
    attempt_id: str
    status: Literal["pending", "complete", "failed"]
    consequence: ConsequenceView
    feedback: FeedbackBody | None
    rating: str | None
    retry_available: bool
    scenario_title: str
    learn_takeaway_title: str | None = None


class RatingRequest(ApiModel):
    rating: Literal["useful", "not_useful"]


# --- Progress / history -----------------------------------------------------


class ActivityDay(ApiModel):
    local_date: str
    state: Literal["completed", "missed", "today", "upcoming"]


class ProgressResponse(ApiModel):
    level: int
    total_xp: int
    xp_for_next_level: int | None
    completed_count: int
    streak_count: int
    activity: list[ActivityDay]
    skills: list[SkillView]
    footnote: str


class HistoryItem(ApiModel):
    attempt_id: str
    scenario_id: str
    title: str
    local_date: str
    primary_skill: str
    primary_skill_label: str
    level: str
    score: int | None
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
