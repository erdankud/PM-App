"""Deterministic offline evaluator — DEVELOPMENT ONLY.

This is not AI feedback and must never be presented as such. It exists so the full
client journey can be exercised without a provider key. `get_settings()` refuses to
start in production with EVALUATOR_PROVIDER=mock.
"""

from __future__ import annotations

import json
import re

from app import practice_catalogue
from app.ai import practice_mock
from app.ai.base import EvaluationRequest, ProviderError, ProviderResponse
from app.i18n import Language
from app.models import SKILL_KEYS

# Both languages are matched by the same patterns. Without the Russian alternatives a
# Russian answer would score systematically lower for saying the same thing, which would
# make the stub misleading rather than merely approximate.
_TRADEOFF = re.compile(
    r"\b(trade[- ]?off|instead of|at the cost of|in exchange|rather than|downside|"
    r"risk|accept(ing)?|sacrific"
    r"|компромисс|размен|ценой|взамен|вместо|минус|риск|жертв|отказыва|уступ)\w*",
    re.IGNORECASE,
)
_NEXT_STEP = re.compile(
    r"\b(measure|monitor|watch|validate|test|experiment|holdout|follow[- ]up|"
    r"if .* (then|i would)|would change my mind|revisit"
    r"|измер|отслежив|мониторин|провер|валидир|тест|эксперимент|холдаут|"
    r"следил|верн[уё]мся|пересмотр)\w*",
    re.IGNORECASE,
)
_UNCERTAINTY = re.compile(
    r"\b(confound|correlat|causal|sample|not significant|uncertain|assum|caveat|"
    r"self[- ]select|small sample|interval"
    r"|искажен|корреляц|причинн|выборк|значим|неопредел|допущен|предполож|"
    r"оговорк|самоотбор|доверительн)\w*",
    re.IGNORECASE,
)
_NUMBERS = re.compile(r"\d")


def _bounded(value: float, low: int, high: int) -> int:
    return int(max(low, min(high, round(value))))


_COPY = {
    Language.EN: {
        "tradeoff_title": "You named the trade-off",
        "tradeoff_detail": (
            "You said what you were giving up rather than presenting the choice as free, "
            "which is what makes a recommendation reviewable by someone else."
        ),
        "coverage_title": "You looked at the evidence before deciding",
        "coverage_detail": (
            "You reviewed {reviewed} of {total} signals, so your argument rests on the "
            "material rather than on instinct."
        ),
        "committed_title": "You committed to a decision",
        "committed_detail": (
            "You picked an option rather than listing considerations, which is the harder "
            "half of the job."
        ),
        "limits_title": "Say what the evidence cannot support",
        "limits_detail": (
            "Name the confound, the sample limit or the missing control so a reader knows "
            "how much weight your argument can carry."
        ),
        "measure_title": "Add what you would measure next",
        "measure_detail": (
            "State the signal that would confirm or reject your read, and what you would "
            "do if it went the other way."
        ),
        "opening_title": "Tighten the opening",
        "opening_detail": (
            "Lead with the recommendation in one sentence, then the single strongest piece "
            "of evidence behind it."
        ),
        "sharper": (
            "State your recommendation first, then the one piece of evidence that most "
            "supports it and the one that argues against. Say explicitly what you are "
            "trading away by choosing it. Finish with the measurement that would tell you "
            "within a few weeks whether you were right."
        ),
    },
    Language.RU: {
        "tradeoff_title": "Вы назвали компромисс",
        "tradeoff_detail": (
            "Вы сказали, чем жертвуете, а не подали выбор как бесплатный — именно это "
            "позволяет другому человеку проверить вашу рекомендацию."
        ),
        "coverage_title": "Вы изучили данные до решения",
        "coverage_detail": (
            "Вы открыли {reviewed} из {total} сигналов, так что аргумент опирается на "
            "материал, а не на интуицию."
        ),
        "committed_title": "Вы дошли до решения",
        "committed_detail": (
            "Вы выбрали вариант, а не перечислили соображения — это более трудная "
            "половина работы."
        ),
        "limits_title": "Скажите, чего данные не подтверждают",
        "limits_detail": (
            "Назовите искажающий фактор, ограничение выборки или отсутствие контрольной "
            "группы, чтобы читатель понимал вес вашего аргумента."
        ),
        "measure_title": "Добавьте, что будете измерять дальше",
        "measure_detail": (
            "Назовите сигнал, который подтвердит или опровергнет вашу трактовку, и что "
            "вы сделаете, если он окажется противоположным."
        ),
        "opening_title": "Подтяните первое предложение",
        "opening_detail": (
            "Начните с рекомендации в одном предложении, а следом дайте самый сильный "
            "довод в её пользу."
        ),
        "sharper": (
            "Сначала назовите рекомендацию, затем один самый сильный довод за неё и один "
            "против. Прямо скажите, чем жертвуете, выбирая её. Закончите тем измерением, "
            "которое за пару недель покажет, были ли вы правы."
        ),
    },
}


class MockEvaluator:
    name = "mock"

    def evaluate(self, request: EvaluationRequest) -> ProviderResponse:
        context = request.context
        # Practice просит у той же ручки другую работу: сначала задачу, потом её
        # разбор. Ветка здесь, а не отдельным провайдером, потому что выбор
        # провайдера — это конфигурация, и заводить вторую настройку ради заглушки
        # значило бы уметь собрать конфигурацию, где разбор гейта живой, а
        # тренировка нет.
        practice = context.get("practice")
        if practice:
            track = practice_catalogue.track(practice["track"])
            if track is None:
                raise ProviderError("practice_track_unknown", practice["track"], retryable=False)
            if practice["stage"] == "brief":
                text = practice_mock.brief(track, int(practice.get("sequence", 0)))
            else:
                text = practice_mock.feedback(track, practice.get("answers", {}))
            return ProviderResponse(raw_text=text, model_id="mock")

        language = Language.coerce(context.get("language"))
        copy = _COPY.get(language, _COPY[Language.EN])
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

        primary = context.get("primary_skill", "discovery")
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
        # Naming what the data cannot support is a discovery skill; naming what you
        # would measure next is a growth one.
        if uncertainty:
            deltas["discovery"] = max(deltas["discovery"], 2)
        if next_step:
            deltas["growth"] = max(deltas["growth"], 2)

        strengths = []
        improvements = []
        if tradeoff:
            strengths.append(
                {
                    "title": copy["tradeoff_title"],
                    "detail": copy["tradeoff_detail"],
                }
            )
        if coverage >= 0.75:
            strengths.append(
                {
                    "title": copy["coverage_title"],
                    "detail": copy["coverage_detail"].format(
                        reviewed=len(reviewed), total=total_cards
                    ),
                }
            )
        if not strengths:
            strengths.append(
                {
                    "title": copy["committed_title"],
                    "detail": copy["committed_detail"],
                }
            )

        if not uncertainty:
            improvements.append(
                {"title": copy["limits_title"], "detail": copy["limits_detail"]}
            )
        if not next_step:
            improvements.append(
                {"title": copy["measure_title"], "detail": copy["measure_detail"]}
            )
        if not improvements:
            improvements.append(
                {"title": copy["opening_title"], "detail": copy["opening_detail"]}
            )

        payload = {
            "rationale_score": rationale_score,
            "communication_score": communication_score,
            "strengths": strengths[:2],
            "improvements": improvements[:2],
            "sharper_approach": copy["sharper"],
            "skill_deltas": deltas,
            "needs_retry": needs_retry,
        }
        return ProviderResponse(
            raw_text=json.dumps(payload, ensure_ascii=False),
            model_id="mock-deterministic-v1",
        )
