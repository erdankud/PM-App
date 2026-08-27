"""Attempt scoring, XP and levels — server-owned (spec §12).

Component budget, total 100:
    evidence engagement   0-15   computed here from recorded interactions
    decision quality      0-25   authored option weight
    rationale quality     0-45   AI rubric
    communication clarity 0-15   AI rubric

Nothing in this module may run on the client.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.i18n import Language

EVIDENCE_MAX = 15
DECISION_MAX = 25
RATIONALE_MAX = 45
COMMUNICATION_MAX = 15

SKILL_DELTA_MIN = -3
SKILL_DELTA_MAX = 8


@dataclass(frozen=True)
class ScoreBreakdown:
    evidence: int
    decision: int
    rationale: int
    communication: int

    @property
    def total(self) -> int:
        return self.evidence + self.decision + self.rationale + self.communication


def evidence_points(opened_count: int, total_cards: int) -> int:
    """First reviewed card earns a third of the budget; the rest scales to the cap.

    Reviewing every card is worth the full 15; reviewing none is worth 0. The curve
    rewards investigation without making a completionist sweep the only good answer.
    """
    if total_cards <= 0 or opened_count <= 0:
        return 0
    opened = min(opened_count, total_cards)
    if total_cards == 1:
        return EVIDENCE_MAX
    base = 5
    span = EVIDENCE_MAX - base
    return int(round(base + span * (opened - 1) / (total_cards - 1)))


def decision_points(scenario_content: dict, option_id: str) -> int:
    for option in scenario_content["decisionOptions"]:
        if option["id"] == option_id:
            return int(max(0, min(DECISION_MAX, option["decisionPoints"])))
    raise KeyError(f"unknown decision option '{option_id}'")


def clamp_rationale(value: float) -> int:
    return int(max(0, min(RATIONALE_MAX, round(value))))


def clamp_communication(value: float) -> int:
    return int(max(0, min(COMMUNICATION_MAX, round(value))))


def clamp_skill_delta(value: float) -> int:
    return int(max(SKILL_DELTA_MIN, min(SKILL_DELTA_MAX, round(value))))


def build_breakdown(
    evidence: int, decision: int, rationale: float, communication: float
) -> ScoreBreakdown:
    return ScoreBreakdown(
        evidence=int(max(0, min(EVIDENCE_MAX, evidence))),
        decision=int(max(0, min(DECISION_MAX, decision))),
        rationale=clamp_rationale(rationale),
        communication=clamp_communication(communication),
    )


def xp_for_score(score: int) -> tuple[int, int]:
    """Return (base_xp, quality_bonus). Quality bonus is 1 XP per point above 50."""
    base = settings.xp_base_completion
    bonus = max(0, min(settings.xp_quality_bonus_cap, score - 50))
    return base, bonus


def level_for_xp(total_xp: int) -> int:
    thresholds = list(settings.level_thresholds)
    level = 1
    for index, threshold in enumerate(thresholds, start=1):
        if total_xp >= threshold:
            level = index
    if total_xp < thresholds[-1]:
        return level
    extra = total_xp - thresholds[-1]
    return len(thresholds) + extra // settings.level_step_after_thresholds


def xp_for_next_level(total_xp: int) -> int | None:
    """XP total at which the next level begins, or None if unbounded config."""
    thresholds = list(settings.level_thresholds)
    for threshold in thresholds:
        if total_xp < threshold:
            return threshold
    steps = (total_xp - thresholds[-1]) // settings.level_step_after_thresholds + 1
    return thresholds[-1] + steps * settings.level_step_after_thresholds


_BANDS: dict[str, dict[Language, str]] = {
    "strong": {Language.EN: "Strong reasoning", Language.RU: "Сильная аргументация"},
    "solid": {Language.EN: "Solid reasoning", Language.RU: "Уверенная аргументация"},
    "developing": {
        Language.EN: "Developing reasoning",
        Language.RU: "Растущая аргументация",
    },
    "early": {Language.EN: "Early reasoning", Language.RU: "Ранняя аргументация"},
    "thin": {
        Language.EN: "Needs a fuller argument",
        Language.RU: "Нужна более полная аргументация",
    },
}


def band_key(score: int) -> str:
    if score >= 85:
        return "strong"
    if score >= 70:
        return "solid"
    if score >= 55:
        return "developing"
    if score >= 40:
        return "early"
    return "thin"


def score_band(score: int, language: Language = Language.EN) -> str:
    """Plain-language band shown next to the numeric score (spec §10.10)."""
    entry = _BANDS[band_key(score)]
    return entry.get(language, entry[Language.EN])
