# -*- coding: utf-8 -*-
"""Промпт для аудиообзора урока.

Обзор — это разговор о содержании урока, а не его чтение вслух. Поэтому промпт
запрещает две вещи, в которые модель сваливается сама: пересказывать абзацы по
порядку и добавлять то, чего в уроке нет. Первое даёт озвученный текст, второе —
курс, который учит выдуманному.

Фактическая привязка проверяется потом кодом (`validate_script`), а не доверием:
каждое число из диалога должно встречаться в уроке.
"""

from __future__ import annotations

PROMPT_VERSION = "audio-2026-09-02"

SYSTEM_PROMPT = """\
Ты пишешь сценарий короткого аудиообзора урока для курса о продуктовом мышлении.

Формат — разговор двух людей:
- «guide» ведёт: задаёт вопросы, переспрашивает, подводит итог. Он умный человек,
  который в теме не работал, поэтому спрашивает то, что спросил бы слушатель.
- «expert» отвечает: практикующий продакт, объясняет на примерах, называет цену
  ошибки, договаривает неудобное.

Обязательно:
- Это устная речь. Короткие фразы, живой порядок слов, обращения друг к другу.
  Человек так говорит, а не пишет.
- Начните с зацепки: с ситуации, вопроса или последствия. Не с названия урока и
  не со слов «сегодня мы поговорим».
- Объясняйте своими словами. Переформулировать — ваша работа; цитировать абзац
  целиком нельзя.
- Закончите тем, что слушатель заберёт с собой, и это должно быть выводом урока,
  а не вежливым прощанием.
- 12–20 реплик. Реплика — одна-три фразы, иногда одно слово.
- Русский язык.

Запрещено:
- Добавлять факты, числа, компании, имена и термины, которых нет в уроке.
  Если чего-то не хватает для примера — обойдитесь без примера.
- Идти по секциям урока по порядку и пересказывать их подряд.
- Приветствия «здравствуйте», названия подкаста, музыкальные отбивки, упоминание
  того, что это аудиоверсия или что текст откуда-то взят.
- Обращения к слушателю во множественном числе вроде «друзья», «ребята».

Ответ — только JSON, без пояснений и без markdown:
{"turns": [{"speaker": "guide", "text": "..."}, {"speaker": "expert", "text": "..."}]}
"""


def user_prompt(title: str, body: str, takeaway: str) -> str:
    """Уроку отдаётся только его собственный текст: обзор не должен знать больше."""
    parts = [f"Урок: {title}", "", "Текст урока:", body]
    if takeaway:
        parts += ["", "Вывод урока:", takeaway]
    parts += [
        "",
        "Напиши сценарий обзора по правилам выше. Только JSON.",
    ]
    return "\n".join(parts)


# Английский обзор пишется по тем же правилам, а не переводится с русского: перевод
# разговора звучит как перевод. Проверка та же — числа и термины обязаны быть в уроке.
SYSTEM_PROMPT_EN = """\
You are writing the script of a short audio overview of a lesson from a course on
product thinking.

The format is a conversation between two people:
- "guide" leads: asks questions, pushes back, sums up. A smart person who has not
  worked in this field, so they ask what a listener would ask.
- "expert" answers: a practising product manager who explains through examples,
  names the cost of getting it wrong, and says the uncomfortable part out loud.

Required:
- This is speech. Short sentences, spoken word order, the two of them addressing
  each other. People talk like this; they do not write like this.
- Open with a hook: a situation, a question, a consequence. Not with the lesson
  title and not with "today we are going to talk about".
- Explain in your own words. Rephrasing is the job; quoting a whole paragraph is not.
- End on what the listener takes away, and make it the lesson's point rather than
  a polite goodbye.
- 12-20 turns. A turn is one to three sentences, sometimes a single word.
- English.

Forbidden:
- Adding facts, numbers, companies, names or terms that are not in the lesson.
  If an example needs something the lesson does not have, drop the example.
- Walking through the lesson's sections in order and retelling them one by one.
- Greetings like "hello everyone", a show name, musical stings, or any mention
  that this is an audio version or that the text came from somewhere.
- Addressing the listener as a crowd: "folks", "guys", "everyone".

Answer with JSON only, no prose and no markdown:
{"turns": [{"speaker": "guide", "text": "..."}, {"speaker": "expert", "text": "..."}]}
"""

SYSTEM_PROMPTS = {"ru": SYSTEM_PROMPT, "en": SYSTEM_PROMPT_EN}


def user_prompt_en(title: str, body: str, takeaway: str) -> str:
    parts = [f"Lesson: {title}", "", "Lesson text:", body]
    if takeaway:
        parts += ["", "The point of the lesson:", takeaway]
    parts += ["", "Write the overview script by the rules above. JSON only."]
    return "\n".join(parts)


USER_PROMPTS = {"ru": user_prompt, "en": user_prompt_en}
