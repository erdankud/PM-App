"""Content language (spec §11).

The language is a stored profile preference rather than a per-request header. Two
reasons: the evaluation worker runs long after the request that triggered it and has
to know which language to write coaching in, and `Accept-Language` is sent by default
by most HTTP clients, so honouring it would silently override a deliberate in-app
choice.

Scenario and assessment text is authored in both languages and checked in; nothing
here is machine-translated at runtime. That keeps the authored consequence (spec §10.9)
independent of any model or provider being reachable.
"""

from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    EN = "en"
    RU = "ru"

    @classmethod
    def coerce(cls, value: str | None) -> "Language":
        """Never raises: an unknown or missing value falls back to English."""
        if not value:
            return cls.EN
        try:
            return cls(value.split("-", 1)[0].lower())
        except ValueError:
            return cls.EN

    @property
    def name_for_model(self) -> str:
        """How the language is named to an evaluation provider."""
        return {Language.EN: "English", Language.RU: "Russian"}[self]


DEFAULT_LANGUAGE = Language.EN

# Copy the server owns rather than the client, because it travels with the payload it
# describes and has to stay truthful about what the server actually did.
_COPY: dict[str, dict[Language, str]] = {
    "what_good_looks_like": {
        Language.EN: "Use the evidence, make a trade-off, and explain your choice.",
        Language.RU: (
            "Опирайтесь на данные, обозначьте компромисс и объясните свой выбор."
        ),
    },
    "progress_footnote": {
        Language.EN: (
            "Skill scores are practice signals based on your in-app work, not an "
            "assessment of job readiness."
        ),
        Language.RU: (
            "Оценки навыков — это сигналы о вашей практике в приложении, а не оценка "
            "готовности к работе."
        ),
    },
    "path_disclaimer": {
        Language.EN: (
            "This is a starting point based on three short questions, not a validated "
            "assessment. It only affects which scenarios you see first."
        ),
        Language.RU: (
            "Это отправная точка по трём коротким вопросам, а не валидированный тест. "
            "Она влияет только на то, какие сценарии вы увидите первыми."
        ),
    },
}


def copy(key: str, language: Language) -> str:
    """Server-owned UI copy. Missing translations fall back to English, never to a key."""
    entry = _COPY[key]
    return entry.get(language, entry[Language.EN])


# The first tag of a scenario becomes the context chip on the Today card.
_TAG_LABELS: dict[str, dict[Language, str]] = {
    "activation": {Language.EN: "Activation", Language.RU: "Активация"},
    "adoption": {Language.EN: "Adoption", Language.RU: "Освоение"},
    "ai": {Language.EN: "AI", Language.RU: "ИИ"},
    "b2b": {Language.EN: "B2B", Language.RU: "B2B"},
    "b2c": {Language.EN: "B2C", Language.RU: "B2C"},
    "beta": {Language.EN: "Beta", Language.RU: "Бета"},
    "churn": {Language.EN: "Churn", Language.RU: "Отток"},
    "customers": {Language.EN: "Customers", Language.RU: "Клиенты"},
    "dashboard": {Language.EN: "Dashboard", Language.RU: "Дашборд"},
    "decision-making": {Language.EN: "Decision Making", Language.RU: "Принятие решений"},
    "delivery": {Language.EN: "Delivery", Language.RU: "Поставка"},
    "discovery": {Language.EN: "Discovery", Language.RU: "Дискавери"},
    "expectations": {Language.EN: "Expectations", Language.RU: "Ожидания"},
    "experiment": {Language.EN: "Experiment", Language.RU: "Эксперимент"},
    "experimentation": {Language.EN: "Experimentation", Language.RU: "Эксперименты"},
    "funnel": {Language.EN: "Funnel", Language.RU: "Воронка"},
    "growth": {Language.EN: "Growth", Language.RU: "Рост"},
    "incidents": {Language.EN: "Incidents", Language.RU: "Инциденты"},
    "launch": {Language.EN: "Launch", Language.RU: "Запуск"},
    "marketplace": {Language.EN: "Marketplace", Language.RU: "Маркетплейс"},
    "metrics": {Language.EN: "Metrics", Language.RU: "Метрики"},
    "mobile": {Language.EN: "Mobile", Language.RU: "Мобильные"},
    "onboarding": {Language.EN: "Onboarding", Language.RU: "Онбординг"},
    "platform": {Language.EN: "Platform", Language.RU: "Платформа"},
    "quality": {Language.EN: "Quality", Language.RU: "Качество"},
    "reliability": {Language.EN: "Reliability", Language.RU: "Надёжность"},
    "research": {Language.EN: "Research", Language.RU: "Исследования"},
    "retention": {Language.EN: "Retention", Language.RU: "Удержание"},
    "risk": {Language.EN: "Risk", Language.RU: "Риск"},
    "roadmap": {Language.EN: "Roadmap", Language.RU: "Роадмап"},
    "scope": {Language.EN: "Scope", Language.RU: "Объём работ"},
    "segments": {Language.EN: "Segments", Language.RU: "Сегменты"},
    "signup": {Language.EN: "Signup", Language.RU: "Регистрация"},
    "stakeholders": {Language.EN: "Stakeholders", Language.RU: "Стейкхолдеры"},
    "statistics": {Language.EN: "Statistics", Language.RU: "Статистика"},
    "strategy": {Language.EN: "Strategy", Language.RU: "Стратегия"},
    "supply": {Language.EN: "Supply", Language.RU: "Предложение"},
    "technical-debt": {Language.EN: "Technical Debt", Language.RU: "Техдолг"},
    "trade-offs": {Language.EN: "Trade-offs", Language.RU: "Компромиссы"},
    "updates": {Language.EN: "Updates", Language.RU: "Коммуникация статуса"},
}


def tag_label(tag: str, language: Language) -> str:
    entry = _TAG_LABELS.get(tag)
    if entry is None:
        return tag.replace("-", " ").title()
    return entry.get(language, entry[Language.EN])
