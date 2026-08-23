"""Skill baselines, deltas and the append-only assessment ledger (spec §12)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.content import assessment_content
from app.models import SKILL_KEYS, SkillAssessment, SkillScore, utcnow

SKILL_LABELS: dict[str, str] = {
    "product_sense": "Product Sense",
    "analytics": "Analytics",
    "user_research": "User Research",
    "prioritization": "Prioritisation",
    "execution": "Execution",
    "communication": "Communication",
}


def get_scores(db: Session, user_id: str) -> dict[str, int]:
    rows = db.query(SkillScore).filter(SkillScore.user_id == user_id).all()
    scores = {row.skill_key: row.score for row in rows}
    return {key: scores.get(key, 50) for key in SKILL_KEYS}


def initialise_from_assessment(
    db: Session, user_id: str, responses: dict[str, str]
) -> dict[str, int]:
    """Compute baselines from author-defined option weights.

    `responses` maps assessment item id -> chosen option id. No AI call is made
    during onboarding (spec §10.3).
    """
    content = assessment_content()
    base = int(content["baselineScore"])
    low = int(content["baselineMin"])
    high = int(content["baselineMax"])

    totals = {key: 0 for key in SKILL_KEYS}
    for item in content["items"]:
        choice_id = responses.get(item["id"])
        if choice_id is None:
            continue
        option = next((o for o in item["options"] if o["id"] == choice_id), None)
        if option is None:
            continue
        for key, weight in option["skillWeights"].items():
            totals[key] += int(weight)

    baselines: dict[str, int] = {}
    for key in SKILL_KEYS:
        baselines[key] = max(low, min(high, base + totals[key]))

    existing = {
        row.skill_key: row
        for row in db.query(SkillScore).filter(SkillScore.user_id == user_id).all()
    }
    for key, value in baselines.items():
        row = existing.get(key)
        if row is None:
            db.add(SkillScore(user_id=user_id, skill_key=key, score=value))
        else:
            row.score = value
            row.updated_at = utcnow()
        db.add(
            SkillAssessment(
                user_id=user_id,
                source="onboarding_assessment",
                skill_key=key,
                delta=value - base,
                reason_code="assessment_baseline",
            )
        )
    return baselines


def starting_level(baselines: dict[str, int]) -> str:
    content = assessment_content()
    average = sum(baselines.values()) / max(1, len(baselines))
    for band in content["levelBands"]:
        if average <= band["maxAverage"]:
            return str(band["level"])
    return "developing"


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
