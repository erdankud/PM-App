"""Skill baselines, deltas and the append-only assessment ledger (spec §12)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.i18n import Language
from app.models import SKILL_KEYS, SkillAssessment, SkillScore, utcnow

SKILL_LABELS: dict[str, str] = {
    "discovery": "Discovery & Research",
    "value_design": "Value & Solution Design",
    "delivery": "Development & Delivery",
    "marketing": "Product Marketing",
    "growth": "Growth & Experiments",
    "economics": "Sales & Economics",
    "communication": "Communication",
    "system_design": "System Design",
}

SKILL_LABELS_RU: dict[str, str] = {
    "discovery": "Дискавери и исследования",
    "value_design": "Ценность и проектирование",
    "delivery": "Разработка и поставка",
    "marketing": "Продуктовый маркетинг",
    "growth": "Рост и эксперименты",
    "economics": "Продажи и экономика",
    "communication": "Коммуникация",
    "system_design": "Системный дизайн",
}

_LABELS_BY_LANGUAGE = {
    Language.EN: SKILL_LABELS,
    Language.RU: SKILL_LABELS_RU,
}


def label(key: str, language: Language = Language.EN) -> str:
    """Display name for a skill key. Unknown keys are returned as-is."""
    return _LABELS_BY_LANGUAGE.get(language, SKILL_LABELS).get(
        key, SKILL_LABELS.get(key, key)
    )


def get_scores(db: Session, user_id: str) -> dict[str, int]:
    rows = db.query(SkillScore).filter(SkillScore.user_id == user_id).all()
    scores = {row.skill_key: row.score for row in rows}
    return {key: scores.get(key, 50) for key in SKILL_KEYS}


def focus_skills(scores: dict[str, int]) -> list[str]:
    """The two lowest skills; ties broken by the canonical skill order."""
    ordered = sorted(SKILL_KEYS, key=lambda key: (scores.get(key, 50), SKILL_KEYS.index(key)))
    return ordered[:2]


def apply_deltas(
    db: Session,
    user_id: str,
    attempt_id: str,
    scenario_id: str,
    deltas: dict[str, int],
) -> dict[str, int]:
    """Apply bounded deltas, write the ledger, and return the new aggregate scores.

    Callers must have already clamped deltas to the allowed range; this function
    clamps again so a bad provider response can never move a score out of bounds.
    """
    from app.services.scoring import clamp_skill_delta

    existing = {
        row.skill_key: row
        for row in db.query(SkillScore).filter(SkillScore.user_id == user_id).all()
    }
    applied: dict[str, int] = {}
    for key in SKILL_KEYS:
        delta = clamp_skill_delta(deltas.get(key, 0))
        if delta == 0:
            continue
        row = existing.get(key)
        if row is None:
            row = SkillScore(user_id=user_id, skill_key=key, score=50)
            db.add(row)
            existing[key] = row
        row.score = max(0, min(100, row.score + delta))
        row.updated_at = utcnow()
        applied[key] = delta
        db.add(
            SkillAssessment(
                user_id=user_id,
                source="attempt",
                scenario_id=scenario_id,
                attempt_id=attempt_id,
                skill_key=key,
                delta=delta,
                reason_code="ai_evaluation",
            )
        )
    return applied


def trends(db: Session, user_id: str, window: int = 5) -> dict[str, str]:
    """Up / down / steady per skill, from the last `window` evaluated attempts."""
    rows = (
        db.query(SkillAssessment)
        .filter(
            SkillAssessment.user_id == user_id,
            SkillAssessment.source == "attempt",
        )
        .order_by(SkillAssessment.created_at.desc())
        .limit(window * len(SKILL_KEYS))
        .all()
    )
    recent_attempts: list[str] = []
    for row in rows:
        if row.attempt_id and row.attempt_id not in recent_attempts:
            recent_attempts.append(row.attempt_id)
        if len(recent_attempts) >= window:
            break
    considered = set(recent_attempts)

    sums = {key: 0 for key in SKILL_KEYS}
    for row in rows:
        if row.attempt_id in considered:
            sums[row.skill_key] = sums.get(row.skill_key, 0) + row.delta

    result: dict[str, str] = {}
    for key in SKILL_KEYS:
        total = sums.get(key, 0)
        result[key] = "up" if total > 0 else "down" if total < 0 else "steady"
    return result
