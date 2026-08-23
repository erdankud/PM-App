"""Deterministic offline evaluator — DEVELOPMENT ONLY.

This is not AI feedback and must never be presented as such. It exists so the full
client journey can be exercised without a provider key. `get_settings()` refuses to
start in production with EVALUATOR_PROVIDER=mock.
"""

from __future__ import annotations

import json
import re

from app.ai.base import EvaluationRequest, ProviderResponse
from app.models import SKILL_KEYS

_TRADEOFF = re.compile(
    r"\b(trade[- ]?off|instead of|at the cost of|in exchange|rather than|downside|"
    r"risk|accept(ing)?|sacrific)\w*", re.IGNORECASE
)
_NEXT_STEP = re.compile(
    r"\b(measure|monitor|watch|validate|test|experiment|holdout|follow[- ]up|"
    r"if .* (then|i would)|would change my mind|revisit)\w*", re.IGNORECASE
)
_UNCERTAINTY = re.compile(
    r"\b(confound|correlat|causal|sample|not significant|uncertain|assum|caveat|"
    r"self[- ]select|small sample|interval)\w*", re.IGNORECASE
)
_NUMBERS = re.compile(r"\d")


def _bounded(value: float, low: int, high: int) -> int:
    return int(max(low, min(high, round(value))))


class MockEvaluator:
    name = "mock"

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        context = request.context
        rationale: str = context.get("rationale", "")
        reviewed: list[str] = context.get("reviewed_evidence_ids", [])
        total_cards: int = context.get("total_evidence_cards", 1) or 1
        decision_points: int = context.get("decision_points", 0)

        words = len(rationale.split())
        length_component = min(1.0, words / 140)
        tradeoff = 1.0 if _TRADEOFF.search(rationale) else 0.0
        next_step = 1.0 if _NEXT_STEP.search(rationale) else 0.0
        uncertainty = 1.0 if _UNCERTAINTY.search(rationale) else 0.0
        specificity = 1.0 if _NUMBERS.search(rationale) else 0.0
        coverage = len(reviewed) / total_cards

        rationale_score = _bounded(
            6
            + 13 * length_component
            + 7 * tradeoff
            + 6 * next_step
            + 5 * uncertainty
            + 4 * specificity
            + 4 * coverage,
            0,
            45,
        )
        concision_penalty = 3 if words > 260 else 0
        communication_score = _bounded(
            4 + 6 * length_component + 3 * specificity + 2 * tradeoff - concision_penalty,
            0,
            15,
        )

        needs_retry = words < 12

        primary = context.get("primary_skill", "product_sense")
        secondary = context.get("secondary_skills", []) or []
        quality = (rationale_score / 45 + decision_points / 25) / 2

        deltas = {key: 0 for key in SKILL_KEYS}
        deltas[primary] = _bounded(-1 + 8 * quality, -3, 8)
        for key in secondary[:2]:
            deltas[key] = _bounded(-1 + 5 * quality, -3, 8)
        deltas["communication"] = max(
            deltas.get("communication", 0),
            _bounded(-1 + 7 * (communication_score / 15), -3, 8),
        )
        if uncertainty:
            deltas["analytics"] = max(deltas["analytics"], 2)
        if next_step:
            deltas["execution"] = max(deltas["execution"], 2)

        strengths = []
        improvements = []
        if tradeoff:
            strengths.append(
                {
                    "title": "You named the trade-off",
                    "detail": "You said what you were giving up rather than presenting "
                    "the choice as free, which is what makes a recommendation "
                    "reviewable by someone else.",
                }
            )
        if coverage >= 0.75:
            strengths.append(
                {
                    "title": "You looked at the evidence before deciding",
                    "detail": f"You reviewed {len(reviewed)} of {total_cards} signals, so "
                    "your argument rests on the material rather than on instinct.",
                }
            )
        if not strengths:
            strengths.append(
                {
                    "title": "You committed to a decision",
                    "detail": "You picked an option rather than listing considerations, "
                    "which is the harder half of the job.",
                }
            )

        if not uncertainty:
            improvements.append(
                {
                    "title": "Say what the evidence cannot support",
                    "detail": "Name the confound, the sample limit or the missing control "
                    "so a reader knows how much weight your argument can carry.",
                }
            )
        if not next_step:
            improvements.append(
                {
                    "title": "Add what you would measure next",
                    "detail": "State the signal that would confirm or reject your read, "
                    "and what you would do if it went the other way.",
                }
            )
        if not improvements:
            improvements.append(
                {
                    "title": "Tighten the opening",
                    "detail": "Lead with the recommendation in one sentence, then the "
                    "single strongest piece of evidence behind it.",
                }
            )

        payload = {
            "rationale_score": rationale_score,
            "communication_score": communication_score,
            "strengths": strengths[:2],
            "improvements": improvements[:2],
            "sharper_approach": (
                "State your recommendation first, then the one piece of evidence that "
                "most supports it and the one that argues against. Say explicitly what "
                "you are trading away by choosing it. Finish with the measurement that "
                "would tell you within a few weeks whether you were right."
            ),
            "skill_deltas": deltas,
            "needs_retry": needs_retry,
        }
        return ProviderResponse(
            raw_text=json.dumps(payload), model_id="mock-deterministic-v1"
        )
