"""Builders that turn stored state into API payloads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import tree_content
from app.i18n import Language, copy
from app.models import ChallengeAttempt, EvidenceInteraction, User, UserProfile
from app.schemas import (
    AttemptView,
    BriefView,
    ChallengeResponse,
    DecisionOptionView,
    EvidenceCardView,
    MeResponse,
    ScenarioView,
    SkillView,
)
from app.services import skills as skills_service
from app.services import tree as tree_service
from app.services.scoring import xp_for_next_level


def what_good_looks_like(language: Language) -> str:
    return copy("what_good_looks_like", language)


def progress_footnote(language: Language) -> str:
    return copy("progress_footnote", language)


def skill_views(
    db: Session,
    user_id: str,
    keys: list[str] | None = None,
    language: Language = Language.EN,
) -> list[SkillView]:
    scores = skills_service.get_scores(db, user_id)
    trend_map = skills_service.trends(db, user_id)
    selected = keys if keys is not None else list(scores.keys())
    return [
        SkillView(
            key=key,
            label=skills_service.label(key, language),
            score=scores.get(key, 50),
            trend=trend_map.get(key, "steady"),
        )
        for key in selected
    ]


def me_response(db: Session, user: User, profile: UserProfile) -> MeResponse:
    language = Language.coerce(profile.language)
    return MeResponse(
        user_id=user.id,
        onboarding_status=user.onboarding_status,
        target_role=profile.target_role,
        timezone=user.timezone,
        current_level=profile.current_level,
        level=profile.level,
        total_xp=profile.total_xp,
        xp_for_next_level=xp_for_next_level(profile.total_xp),
        streak_count=profile.streak_count,
        entitlement=profile.entitlement,
        focus_skills=list(profile.focus_skills or []),
        skills=skill_views(db, user.id, language=language),
        language=language.value,
    )


def attempt_state(attempt: ChallengeAttempt | None) -> str:
    if attempt is None:
        return "not_started"
    if attempt.status == "draft":
        has_progress = bool(attempt.selected_option_id or attempt.rationale)
        return "in_progress" if has_progress else "not_started"
    if attempt.status in {"submitted", "awaiting_feedback", "feedback_failed", "complete"}:
        return attempt.status
    return "not_started"


def gate_scenario(scenario_id: str, language: Language = Language.RU) -> dict | None:
    """Сценарий в языке читателя.

    Оба дерева: сценарии гейтов есть и у карты продукта, и у System Design.
    Оценщик берёт сценарий отдельно и всегда авторский — рубрика существует в одном
    экземпляре, поэтому язык не может изменить балл.
    """
    return tree_content.scenario(scenario_id, language.value)


def challenge_response(
    db: Session, attempt: ChallengeAttempt, language: Language
) -> ChallengeResponse:
    """The gate payload the client renders.

    Consequences and the authored rubric are withheld until submission, exactly as in
    v0.1: seeing the outcome before deciding would remove the decision.
    """
    content = gate_scenario(attempt.scenario_id, language)
    if content is None:
        raise LookupError(attempt.scenario_id)

    reviewed = [
        row.evidence_card_id
        for row in db.query(EvidenceInteraction)
        .filter(EvidenceInteraction.attempt_id == attempt.id)
        .order_by(EvidenceInteraction.opened_at.asc())
    ]
    block = tree_content.block(attempt.block_id, language.value)

    return ChallengeResponse(
        gate_id=attempt.gate_id,
        block_id=attempt.block_id,
        block_title=block["title"] if block else attempt.block_id,
        attempt_index=attempt.attempt_index,
        pass_threshold=tree_service.pass_threshold(
            tree_content.gate(attempt.gate_id) or {}
        ),
        state=attempt_state(attempt),
        scenario=ScenarioView(
            id=content["id"],
            version=content["version"],
            title=content["title"],
            summary=content["summary"],
            estimated_minutes=content["estimatedMinutes"],
            level=content["level"],
            primary_skill=content["primarySkill"],
            primary_skill_label=skills_service.label(content["primarySkill"], language),
            tags=list(content["tags"]),
            brief=BriefView(
                **content["brief"], what_good_looks_like=what_good_looks_like(language)
            ),
            evidence_cards=[
                EvidenceCardView(**card)
                for card in sorted(content["evidenceCards"], key=lambda c: c["order"])
            ],
            decision_prompt=content["decisionPrompt"],
            decision_options=[
                DecisionOptionView(
                    id=option["id"],
                    label=option["label"],
                    description=option["description"],
                )
                for option in content["decisionOptions"]
            ],
        ),
        attempt=AttemptView(
            attempt_id=attempt.id,
            status=attempt.status,
            selected_option_id=attempt.selected_option_id,
            rationale=attempt.rationale,
            reviewed_evidence_ids=reviewed,
        ),
    )
