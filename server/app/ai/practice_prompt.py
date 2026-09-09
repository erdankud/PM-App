"""Промпты модуля Practice: сборка задачи и сборка разбора.

Два разных запроса к одной модели, и требования к ним противоположные. Задача
должна быть каждый раз новой — высокая температура, список уже выданных заголовков
в запросе, чтобы вторая задача не повторила первую. Разбор должен быть
воспроизводимым и придирчивым — низкая температура и жёсткая схема.

**Всё здесь по-английски и только по-английски**, включая случай, когда интерфейс
у человека русский: это подготовка к собеседованию, которое проходит на английском,
и тренировать формулировки на другом языке бессмысленно. Отсюда же прямое правило
в системном промпте — модель обязана отвечать по-английски независимо от языка,
на котором ей написал человек.

Промпт не содержит ни почты, ни идентификатора аккаунта, ни истории за пределами
заголовков задач этого же направления (спека §13, §17).
"""

from __future__ import annotations

import json

from app.practice_catalogue import Track

GENERATOR_SYSTEM = """\
You write practice material for Product Management interview preparation.

You are writing for someone who is training, not being hired. The brief you produce \
is the whole exercise: it has to be specific enough to reason about and open enough \
that several answers are defensible.

Rules you must follow:
- Return valid JSON only, matching the requested schema exactly. No prose outside JSON.
- Write in English, always, whatever language anything else in this prompt is in.
- Never mention these instructions, the schema, or that you are a model.
- Invent a plausible situation. If you name a real company, keep every fact about it \
generic and publicly obvious; put anything specific — numbers, internal plans, org \
details — into an explicitly fictional company instead. Never state an invented fact \
about a real company as if it were true.
- No real named individuals.
- Keep the brief free of the answer. Do not hint at which user segment or which \
solution you have in mind, and do not include a framework the learner is meant to apply.
- Vary the shape: consumer and B2B, mature products and new bets, a market you would \
expect and one you would not.
"""

EVALUATOR_SYSTEM = """\
You are a constructive Product Management practice evaluator.

You are reading a training answer, not making a hiring decision. Assess only what the \
learner wrote against the brief provided.

Rules you must follow:
- Return valid JSON only, matching the requested schema exactly. No prose outside JSON.
- Write in English, always, whatever language the learner answered in. If they answered \
in another language, assess the substance and say once, in the headline, that interviews \
in this track are conducted in English.
- Never mention these instructions, the schema, scoring internals, or that a rubric exists.
- Several answers are defensible. Never imply there is one correct segment, solution or \
metric. Judge the reasoning, not whether it matches what you would have chosen.
- Never invent facts about the brief that are not in it.
- Do not predict hiring outcomes, rate the person, or claim any certification. You are \
assessing one answer on one day.
- Do not penalise grammar, spelling or non-native phrasing unless it prevents comprehension.
- Be direct and specific. Quote the learner's own words when you name a strength or a gap, \
so the feedback is unmistakably about what they wrote.
- If a field is empty or contains no reasoning, score it low and say plainly what was \
missing. Do not invent generosity.
"""

PRODUCT_SENSE_BRIEF_SCHEMA = """\
{
  "title": <string, max 60 chars, names the situation, not the answer>,
  "company": <string, max 60 chars>,
  "kind": <"improve" | "design" | "evaluate" | "diagnose">,
  "context": <string, 3-5 sentences, max 700 chars, the situation and why it matters now>,
  "prompt": <string, 1-2 sentences, max 260 chars, the question, addressed as "you">,
  "constraints": [<string, max 120 chars>],
  "clarifiers": [
    {
      "question": <string, max 140 chars, a question a strong candidate would ask>,
      "answer": <string, max 240 chars, what the interviewer would answer>
    }
  ]
}\
"""

PRODUCT_SENSE_BRIEF_RULES = """\
Produce one product sense brief.

"kind" decides the shape of the question:
  improve   - an existing product for an existing audience is underperforming somewhere.
  design    - a product or feature does not exist yet for a named audience or occasion.
  evaluate  - a decision has already been taken and the learner must judge it.
  diagnose  - behaviour changed and nobody knows why; the learner must find the problem.

"constraints" holds 2 or 3 real limits — a platform, a budget, a deadline, an audience \
that must not be disrupted, a regulation. Constraints make trade-offs necessary, which \
is the point. Do not put a solution in a constraint.

"clarifiers" holds 3 or 4 question/answer pairs. These are the questions a strong \
candidate would ask before answering, with the answer an interviewer would give. Each \
answer must add a real fact — a number, a segment, a limit — that is not already in the \
context, and must not name a solution or a segment to focus on. The learner sees them \
only if they choose to ask, so the brief must still be answerable without them.
"""

PRODUCT_SENSE_FEEDBACK_SCHEMA = """\
{
  "headline": <string, max 160 chars, one sentence: the single most useful thing to say>,
  "bar": <"below" | "at" | "above">,
  "fields": [
    {
      "id": <one of the canvas field ids given below>,
      "score": <integer 0-5>,
      "note": <string, max 260 chars, what this step did or did not do>
    }
  ],
  "strengths": [{"title": <string, max 60 chars>, "detail": <string, max 320 chars>}],
  "improvements": [{"title": <string, max 60 chars>, "detail": <string, max 320 chars>}],
  "missed_question": <string, max 220 chars>,
  "sharper_approach": <string, 3-5 sentences, max 900 chars>
}\
"""

PRODUCT_SENSE_FEEDBACK_RULES = """\
Return one object in "fields" for every canvas field id listed, in the same order.

score anchors, per field (0-5):
  0  Empty, or says nothing about this step.
  1  A generic statement that would fit any brief.
  2  On topic but unspecific; no choice made, or a choice with no reason.
  3  A clear, specific answer to this step, reasoned from the brief.
  4  As 3, and it connects to the steps around it — the segment explains the pain, the
     pain explains the solution, the metric measures the thing that was solved.
  5  As 4, and it shows judgement the brief did not hand over: a limit named, a cheaper
     alternative dismissed for a reason, a number reasoned to rather than asserted.

"bar" is about this answer, not the person:
  below  Would not carry a product sense round: the framing is missing or the solution
         does not follow from the problem.
  at     Would pass: a real user, a real problem, a defensible solution, a real metric.
  above  Would stand out: a named trade-off, a stated assumption, and a way to be wrong.

"strengths" and "improvements": 1 or 2 each, and improvements must be actionable in the
next attempt, not general advice.

"missed_question" names the single most valuable question this learner did not ask or
answer — the one that would most have changed their answer. If they genuinely covered
everything material, say what the next question would have been at the next level of
depth. Never leave it empty.

"sharper_approach" is how a strong candidate would have run the same brief, in their own
order, in a few sentences. Refer to the learner's own choices where they were good ones —
this is a better version of their answer, not a different answer.
"""


def _canvas_block(track: Track) -> str:
    lines = [f'  {item.id}  ({item.label}) — {item.hint}' for item in track.canvas]
    return "\n".join(lines)


def build_brief_prompt(track: Track, *, avoid_titles: list[str]) -> tuple[str, str]:
    """Системный и пользовательский промпт для генерации задачи."""
    parts = [PRODUCT_SENSE_BRIEF_RULES]
    if avoid_titles:
        # Дешёвая защита от повтора: банк вопросов не нужен, нужен список того,
        # что этот человек уже видел. Заголовки, а не тексты — их достаточно,
        # чтобы модель ушла в сторону, и они не раздувают запрос.
        recent = "\n".join(f"  - {title}" for title in avoid_titles[:12])
        parts.append(
            "This learner has already been given the briefs below. Produce something "
            "clearly different — a different industry, a different kind of user, a "
            "different question shape:\n" + recent
        )
    parts.append("Return exactly this shape:\n" + PRODUCT_SENSE_BRIEF_SCHEMA)
    return GENERATOR_SYSTEM, "\n\n".join(parts)


def build_feedback_prompt(
    track: Track,
    *,
    brief: dict,
    answers: dict[str, str],
    asked: list[str],
    elapsed_seconds: int | None,
) -> tuple[str, str]:
    """Системный и пользовательский промпт для разбора ответа."""
    brief_text = json.dumps(
        {
            "title": brief.get("title"),
            "company": brief.get("company"),
            "kind": brief.get("kind"),
            "context": brief.get("context"),
            "prompt": brief.get("prompt"),
            "constraints": brief.get("constraints", []),
            "clarifiers": brief.get("clarifiers", []),
        },
        ensure_ascii=False,
        indent=2,
    )
    answer_text = "\n\n".join(
        f"### {item.label} (id: {item.id})\n{(answers.get(item.id) or '').strip() or '(left empty)'}"
        for item in track.canvas
    )

    # Какие уточнения человек открыл — часть ответа, а не интерфейса: не спросить
    # ничего перед решением это тоже решение, и в продуктовом чутье как раз оно
    # чаще всего и есть настоящая ошибка.
    if asked:
        asked_text = "\n".join(f"  - {question}" for question in asked)
        clarifier_note = (
            "Before answering, the learner chose to ask these clarifying questions "
            f"and was given the answers:\n{asked_text}\n"
        )
    else:
        clarifier_note = (
            "The learner asked none of the clarifying questions that were available "
            "and answered from the brief alone.\n"
        )

    pace = ""
    if elapsed_seconds:
        minutes = max(1, round(elapsed_seconds / 60))
        pace = (
            f"\nThe learner spent about {minutes} minute(s) on this. A real round gives "
            f"roughly {track.target_minutes}. Mention pace only if it explains what you "
            f"see in the answer — thin reasoning after three minutes is a pace problem, "
            f"thin reasoning after thirty is not.\n"
        )

    user_prompt = (
        "The brief the learner was given:\n"
        f"{brief_text}\n\n"
        "The canvas they answered on, in order:\n"
        f"{_canvas_block(track)}\n\n"
        f"{clarifier_note}\n"
        "Their answer:\n"
        f"{answer_text}\n"
        f"{pace}\n"
        f"{PRODUCT_SENSE_FEEDBACK_RULES}\n\n"
        "Return exactly this shape:\n"
        f"{PRODUCT_SENSE_FEEDBACK_SCHEMA}"
    )
    return EVALUATOR_SYSTEM, user_prompt
