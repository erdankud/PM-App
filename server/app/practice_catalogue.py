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

**Шесть форм собраны из двух механизмов, а не из шести.** Первый — уточнения:
вопросы, которые можно задать до ответа, с ответом интервьюера. В продуктовом чутье
это «что вы спросите, прежде чем решать», в аналитике — «какой разрез данных вы
запросите», и это один и тот же механизм с разной вывеской: что человек открыл,
записано и уходит в разбор. Второй — возражение: реплика, которая появляется
**после** того, как позиция занята, и на которую надо ответить, не сменив тему.
Его используют стратегия («executive pushback») и техническая беглость
(«counter-argument»). Больше механизмов заводить не понадобилось, и заводить их
ради разнообразия не нужно: форма существует, чтобы ловить конкретный способ
провалиться, а не чтобы отличаться от соседней.
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
    # Словарь поля `kind` в задаче. Это не украшение: вид задачи задаёт её форму,
    # и проверка отвергает задачу с видом, которого у направления нет.
    kinds: tuple[str, ...] = ()
    # Заголовок и подсказка над уточнениями. По-английски, как и всё содержимое
    # Practice: в аналитике это не «уточняющие вопросы», а запрос разреза данных,
    # и назвать их одинаково значило бы спрятать то, что как раз и тренируется.
    clarifier_title: str = ""
    clarifier_hint: str = ""
    # Возражение. `counter_field` — поле канвы, которым на него отвечают; до него
    # возражение закрыто, и открывается оно, только когда всё, что стоит выше,
    # написано. Иначе это не возражение на позицию, а часть условия задачи.
    counter_field: str | None = None
    counter_title: str = ""
    counter_hint: str = ""

    @property
    def counter_after(self) -> tuple[str, ...]:
        """Поля, которые должны быть заполнены, прежде чем возражение откроется."""
        if self.counter_field is None:
            return ()
        ids = [item.id for item in self.canvas]
        return tuple(ids[: ids.index(self.counter_field)])


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


# Стратегия. Провал здесь почти всегда один и тот же: рекомендация, которая
# рассыпается на первом возражении, потому что позиции под ней не было — был обзор
# рынка. Поэтому ставка стоит отдельным полем, а не выводом из предыдущего абзаца,
# и последним шагом идёт ответ на возражение.
PRODUCT_STRATEGY_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="landscape",
        label="The market as you read it",
        hint="Where does the money sit in this market today, who holds it, and what is changing that makes now different?",
        min_chars=60,
        rows=4,
    ),
    CanvasField(
        id="position",
        label="Where this company can win",
        hint="What does it have that a competitor cannot copy in a year — and what does that make possible that others cannot do?",
        min_chars=50,
        rows=4,
    ),
    CanvasField(
        id="bet",
        label="The bet",
        hint="State the recommendation in two sentences. Say what you are doing and what you are deliberately not doing.",
        min_chars=60,
        rows=4,
    ),
    CanvasField(
        id="sequence",
        label="The first two moves",
        hint="What ships in the next two quarters, and what has to be true before the move after that is worth making?",
        min_chars=60,
        rows=4,
    ),
    CanvasField(
        id="risk",
        label="What would kill it",
        hint="The assumption the bet rests on, and the signal that would make you walk away rather than double down.",
        min_chars=50,
        rows=4,
    ),
    CanvasField(
        id="rebuttal",
        label="Answering the pushback",
        hint="Hold your position or change it — both are respectable. Answering a different question is not.",
        min_chars=60,
        rows=4,
    ),
)


# Аналитика. Здесь тренируется не вывод, а путь к нему: какой разрез данных вы
# запросили и что он исключил. Поэтому гипотезы и разрезы — разные поля: список
# причин без единого разреза это гадание, а разрез без гипотезы — экскурсия.
ANALYTICAL_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="restate",
        label="What actually moved",
        hint="Which number, by how much, over what window — and say plainly what the number does not tell you yet.",
        min_chars=50,
        rows=3,
    ),
    CanvasField(
        id="hypotheses",
        label="What could explain it",
        hint="Three or four candidate causes. Cover more than one family: instrumentation, mix, seasonality, a product change, the outside world.",
        min_chars=70,
        rows=5,
    ),
    CanvasField(
        id="cuts",
        label="How the data separates them",
        hint="For each hypothesis you kept, name the cut you asked for and what it ruled in or out. Say which cut you would ask for next.",
        min_chars=70,
        rows=5,
    ),
    CanvasField(
        id="conclusion",
        label="What you now believe",
        hint="The cause you are willing to name, how confident you are, and the part of the move that is still unexplained.",
        min_chars=50,
        rows=4,
    ),
    CanvasField(
        id="action",
        label="What you would do on Monday",
        hint="The decision this justifies, who you would tell, and what you would do differently if you turn out to be wrong.",
        min_chars=50,
        rows=4,
    ),
)


# Поведенческий раунд. Короткий по времени и тесный по полям намеренно: провал
# здесь не в длине рассказа, а в том, что «мы» вытесняет «я», а результат остаётся
# без числа. Поэтому действия и результат — отдельные поля, а не одна история.
LEADERSHIP_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="situation",
        label="The situation",
        hint="Where you were, what was at stake and who else was in it. Two or three sentences — the story is not the point yet.",
        min_chars=50,
        rows=3,
    ),
    CanvasField(
        id="tension",
        label="What made it hard",
        hint="The specific conflict, constraint or unknown. If anyone would have done the obvious thing, this is the wrong story.",
        min_chars=50,
        rows=3,
    ),
    CanvasField(
        id="actions",
        label="What you did",
        hint="Your own actions, in order, and the one you were least sure about. Say «I» where it was you and «we» only where it was not.",
        min_chars=70,
        rows=5,
    ),
    CanvasField(
        id="outcome",
        label="How it landed",
        hint="The result, with a number if you have one, and how you know. Include the part that did not go well.",
        min_chars=50,
        rows=3,
    ),
    CanvasField(
        id="learning",
        label="What it changed",
        hint="What you do differently now — and where you have already applied it since.",
        min_chars=40,
        rows=3,
    ),
)


# Техническая беглость. Проверяется не знание, а способность объяснить механизм
# названной аудитории и удержать выбор под возражением инженера. Поэтому первое
# поле — объяснение конкретному человеку, а не определение.
TECHNICAL_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="explain",
        label="Explain it plainly",
        hint="Explain the mechanism to the audience the brief names, in words they already use. An analogy is fine if it survives one question about it.",
        min_chars=70,
        rows=5,
    ),
    CanvasField(
        id="boundary",
        label="Where it breaks",
        hint="When does this stop working, and what does the failure look like from the user's side rather than from the logs?",
        min_chars=50,
        rows=4,
    ),
    CanvasField(
        id="choice",
        label="The call you would make",
        hint="Which option you would ship, and the one or two numbers that decide it rather than taste.",
        min_chars=60,
        rows=4,
    ),
    CanvasField(
        id="cost",
        label="What it costs",
        hint="Latency, money, quality or engineering time — name which one you are spending, roughly how much, and who notices.",
        min_chars=40,
        rows=3,
    ),
    CanvasField(
        id="rebuttal",
        label="Answering the counter-argument",
        hint="An engineer disagrees. Concede what is true, then say what you would still ship and why.",
        min_chars=60,
        rows=4,
    ),
)


# Домашнее задание. Это единственное направление, где проверяют письмо, а не речь,
# поэтому поля — разделы документа, а нижние границы длиннее: короткий раздел здесь
# не лаконичность, а пропуск. Ориентир 90 минут стоит в самой задаче, и переработка
# сверх него на реальном собеседовании считается минусом.
TAKE_HOME_CANVAS: tuple[CanvasField, ...] = (
    CanvasField(
        id="summary",
        label="Executive summary",
        hint="The recommendation and the reason for it, in the first five sentences. Assume the reader stops there.",
        min_chars=150,
        rows=5,
    ),
    CanvasField(
        id="evidence",
        label="What the material says",
        hint="What you took from the numbers and quotes you were given — including what they do not support.",
        min_chars=200,
        rows=7,
    ),
    CanvasField(
        id="users",
        label="Who this is for",
        hint="The segments you can see, the one you are prioritising, and who you are choosing not to serve yet.",
        min_chars=150,
        rows=6,
    ),
    CanvasField(
        id="plan",
        label="The plan",
        hint="What ships, in what order, over the horizon the brief names. Say what each stage is for, not just what is in it.",
        min_chars=250,
        rows=8,
    ),
    CanvasField(
        id="metrics",
        label="How you will know",
        hint="Targets and guardrails, and the review point at which you would change course rather than push on.",
        min_chars=120,
        rows=5,
    ),
    CanvasField(
        id="risks",
        label="Risks and what you left out",
        hint="The two risks that would matter most, what you would do about them, and what you deliberately kept out of scope.",
        min_chars=120,
        rows=5,
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
        live=True,
        canvas=PRODUCT_STRATEGY_CANVAS,
        target_minutes=25,
        kinds=("enter", "expand", "defend", "retreat"),
        clarifier_title="What you can ask before you commit",
        clarifier_hint=(
            "Strategy answers get graded on what you assumed. Ask, and the assumption "
            "becomes a fact you were given."
        ),
        counter_field="rebuttal",
        counter_title="Executive pushback",
        counter_hint=(
            "Take the bet first. This is what the leadership team puts to you once you have."
        ),
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
        kinds=("improve", "design", "evaluate", "diagnose"),
        clarifier_title="Clarifying questions",
        clarifier_hint=(
            "Ask before you answer. What you choose to ask is part of what the review reads."
        ),
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
        live=True,
        canvas=ANALYTICAL_CANVAS,
        target_minutes=20,
        kinds=("drop", "spike", "flat", "divergence"),
        clarifier_title="Cuts of the data you can request",
        clarifier_hint=(
            "Every cut comes back with a real answer. Which ones you ask for is the round — "
            "and asking for all of them is an answer too."
        ),
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
        live=True,
        canvas=LEADERSHIP_CANVAS,
        target_minutes=10,
        kinds=("conflict", "failure", "influence", "ambiguity"),
        clarifier_title="What you can ask the interviewer",
        clarifier_hint=(
            "A behavioural prompt is wider than it looks. Asking which part they want is "
            "how you avoid telling the wrong story well."
        ),
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
        live=True,
        canvas=TECHNICAL_CANVAS,
        target_minutes=15,
        kinds=("mechanism", "tradeoff", "failure", "cost"),
        clarifier_title="What you can ask the engineer",
        clarifier_hint=(
            "You are not expected to know the internals. You are expected to know which "
            "detail changes the decision."
        ),
        counter_field="rebuttal",
        counter_title="The counter-argument",
        counter_hint=(
            "Make the call first. Then the engineer who would have to build it answers back."
        ),
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
        live=True,
        canvas=TAKE_HOME_CANVAS,
        target_minutes=90,
        kinds=("roadmap", "launch", "pitch", "turnaround"),
        clarifier_title="What the hiring manager will answer by email",
        clarifier_hint=(
            "A take-home is sent, not sat. Asking the two questions that change the shape "
            "of the document is part of doing it well."
        ),
    ),
)

BY_ID: dict[str, Track] = {track.id: track for track in TRACKS}


def track(track_id: str) -> Track | None:
    return BY_ID.get(track_id)


def live_tracks() -> tuple[Track, ...]:
    return tuple(item for item in TRACKS if item.live)
