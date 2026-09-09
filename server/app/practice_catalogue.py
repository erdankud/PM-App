"""Каталог тренировок модуля Practice.

Шесть направлений подготовки к продуктовому собеседованию. В отличие от карты
навыков это **не курс**: здесь ничего не читают. Каждое направление — своя
симуляция, и формы у них разные не для разнообразия, а потому что провал у каждого
навыка свой. Продуктовое чутьё чаще всего валят прыжком в фичи мимо постановки
задачи — значит, отвечать надо не в поле «текст», а по канве, где постановка стоит
первым шагом и оценивается отдельно. Аналитику валят не текстом вообще, а тем, что
не спрашивают нужный разрез данных — значит, там нужен диалог с данными, а не эссе.

**Каталог живёт в коде, а не в `content/`.** Контент корпуса авторский, русский, и
проходит перевод-наложение; Practice по требованию автора существует только на
английском — язык индустрии, на котором эти собеседования и проходят. Положить его
в `content/` значило бы завести файл, который переводить нельзя, внутри конвейера,
который переводит всё.

Тексты подсказок и разборов здесь не хранятся: их каждый раз пишет модель. Хранится
рамка — что тренируем, какой формы задача, из каких полей состоит ответ.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CanvasField:
    """Одно поле ответа. Порядок полей — это и есть тренируемый порядок мысли."""

    id: str
    label: str
    hint: str
    min_chars: int = 0
    rows: int = 3


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    # Одна строка на плитке: что это за раунд собеседования.
    blurb: str
    # Что именно проверяет интервьюер. Формулировка от второго лица — её читают.
    tests: str
    # Форма симуляции. Пишется здесь, потому что она у каждого направления своя.
    format: str
    # Живое направление или ещё готовится. Плитка «готовится» честнее, чем
    # отсутствие пункта: человек должен видеть весь набор, за которым пришёл.
    live: bool = False
    canvas: tuple[CanvasField, ...] = field(default_factory=tuple)
    # Ориентир по времени, минуты. Не таймер обратного отсчёта: время показывается
    # как факт, а не как угроза — но ответ, написанный за три минуты, объясняется
    # темпом, и разбору об этом полезно знать.
    target_minutes: int = 20


PRODUCT_SENSE_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="goal",
        label="The goal",
        hint="What is the company actually trying to achieve here — and how would that show up in the business?",
        min_chars=40,
        rows=3,
    ),
    CanvasField(
        id="user",
        label="The user",
        hint="Name the segments you can see, pick one, and say why that one and not the others.",
        min_chars=40,
        rows=3,
    ),
    CanvasField(
        id="pain",
        label="The pain",
        hint="What specifically is hard for that segment today? Be concrete about the moment it happens.",
        min_chars=40,
        rows=4,
    ),
    CanvasField(
        id="solutions",
        label="Solutions",
        hint="Two or three ideas that address that pain. Say which one you would build first and why.",
        min_chars=60,
        rows=5,
    ),
    CanvasField(
        id="tradeoff",
        label="The trade-off",
        hint="What are you giving up by choosing it? What would have to be true for this to be the wrong call?",
        min_chars=40,
        rows=4,
    ),
    CanvasField(
        id="metric",
        label="Success",
        hint="One primary metric, and one guardrail that would tell you it worked at someone else's expense.",
        min_chars=30,
        rows=3,
    ),
)


TRACKS: tuple[Track, ...] = (
    Track(
        id="product_strategy",
        title="Product Strategy",
        blurb="Markets, competition and long-term bets.",
        tests=(
            "Whether you can hold a position under pressure: read a market, pick a bet, "
            "and say what would make you abandon it."
        ),
        format="A market brief, your recommendation, and one round of executive pushback.",
        target_minutes=25,
    ),
    Track(
        id="product_sense",
        title="Product Sense",
        blurb="The right users, the right problems, the right solutions.",
        tests=(
            "Whether you frame a problem before you solve it. This is the round with the "
            "widest spread in scores, and the split is almost always the same: strong answers "
            "start with the user and the goal, weak ones start with features."
        ),
        format="A generated brief with clarifying questions you can ask, answered on a six-step canvas.",
        live=True,
        canvas=PRODUCT_SENSE_CANVAS,
        target_minutes=20,
    ),
    Track(
        id="analytical_execution",
        title="Analytics and Execution",
        blurb="Metrics, goals, and decisions on messy data.",
        tests=(
            "Whether you can find the cause of a number that moved. The skill is which cut of "
            "the data you ask for, so this one is a conversation, not an essay."
        ),
        format="A metric moves. You request cuts of the data, receive them, and then conclude.",
        target_minutes=20,
    ),
    Track(
        id="leadership_drive",
        title="Leadership & Drive",
        blurb="Stories that show impact and signal the right level.",
        tests=(
            "Whether your story lands at the level you are interviewing for. Senior means "
            "impact on the team; staff means impact on the org — the same story told at the "
            "wrong altitude reads as a down-level."
        ),
        format="A behavioural prompt, your story, a level read, and the follow-up an interviewer would ask.",
        target_minutes=10,
    ),
    Track(
        id="technical_fluency",
        title="Technical Fluency",
        blurb="Talking about AI and systems without an interpreter.",
        tests=(
            "Whether you can reason about an architecture and defend a trade-off. Since 2026 "
            "that includes evals, hallucinations, retrieval versus fine-tuning, latency and "
            "token cost — in ordinary product rounds, not just technical ones."
        ),
        format="Explain a mechanism to a named audience, then defend a trade-off against a counter-argument.",
        target_minutes=15,
    ),
    Track(
        id="take_home",
        title="Take-Home",
        blurb="Roadmap and pitch exercises, done in a time box.",
        tests=(
            "Whether you can write. Graded on user insight, use of data, business sense, "
            "structure and clarity — and overinvesting past the time box counts against you."
        ),
        format="A longer brief with a stated time box, answered as a structured document.",
        target_minutes=90,
    ),
)

BY_ID: dict[str, Track] = {track.id: track for track in TRACKS}


def track(track_id: str) -> Track | None:
    return BY_ID.get(track_id)


def live_tracks() -> tuple[Track, ...]:
    return tuple(item for item in TRACKS if item.live)
