# -*- coding: utf-8 -*-
"""Перевод корпуса на другой язык: генерация один раз, проверка фактов, хранение как контент.

Текст переводит модель, поэтому здесь же он и проверяется. Доверять переводу нельзя
ровно по той же причине, по какой нельзя доверять аудиосценарию: модель охотно
округляет числа, теряет разметку терминов и «улучшает» примеры. Проверка простая и
жёсткая:

- набор ключей обязан совпасть с исходником — ни одного пропущенного поля;
- каждое число из русского текста обязано найтись в английском, и наоборот;
- идентификаторы терминов в разметке `[[id|подпись]]` обязаны совпасть;
- кириллицы в переводе быть не должно — имена компаний транслитерируются;
- у типизированных упражнений эталон приёмки обязан остаться одним из вариантов.

Последнее — не придирка: `acceptance.expected` сверяется с ответом человека, и если
эталон переведён иначе, чем варианты выбора, упражнение начнёт говорить «иначе, чем
в разборе» на правильный ответ.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.ai.base import ProviderError
from app.i18n_content import CYRILLIC

PROMPT_VERSION = "translate-2026-09-02"

#: Сколько раз переспрашивать модель, когда ответ не прошёл проверку.
MAX_ATTEMPTS = 3

#: Сколько раз повторять сам вызов, когда провайдер не ответил. Это другое:
#: «высокий спрос» (503) или таймаут — не брак ответа, а его отсутствие, и терять
#: на этом целую пачку файлов незачем.
PROVIDER_ATTEMPTS = 4
PROVIDER_BACKOFF_SECONDS = 8.0

SYSTEM_PROMPT = """\
You translate an authored course on product management and system design from
Russian into English. The result is what a learner reads, so it has to read like it
was written in English, not like a translation.

Rules:
- Translate meaning, not words. Keep the author's voice: plain, direct, concrete.
  Short sentences. No corporate padding, no "it is important to note that".
- Keep every number exactly as it is. Do not round, do not convert units, do not
  add a number that is not in the source.
- Keep Latin terms as they are: API, SLA, p95, HEART, RICE, Feedback Matrix, 5 Whys.
- Markup must survive verbatim. `[[term-id|visible label]]` keeps the same term-id;
  translate only the visible label. `**bold**` stays `**bold**`.
- Transliterate invented company and product names rather than translating them:
  «Смена» -> Smena, «Полка» -> Polka, «Диспетчер» -> Dispetcher, «Сурма» -> Surma,
  «Реестр» -> Reestr, «Ветка» -> Vetka, «Кедр» -> Kedr, «Литера» -> Litera.
  Use the same spelling every time.
- English is usually shorter than Russian. If a translation comes out much longer
  than its source, tighten it rather than padding.
- No Cyrillic characters in the output at all.
- Do not add, drop, merge or reorder anything. One input value produces exactly one
  output value.

You are given a JSON object of {"path": "russian text"}. Answer with a JSON object
of {"path": "english text"} using exactly the same keys. JSON only, no prose.
"""


def user_prompt(fields: dict[str, str], note: str = "") -> str:
    parts = []
    if note:
        parts += [note, ""]
    parts += [json.dumps(fields, ensure_ascii=False, indent=1)]
    return "\n".join(parts)


# --- Проверка ----------------------------------------------------------------

_TERM = re.compile(r"\[\[([^|\]]+)\|")


def _numbers(text: str, language: str) -> set[float]:
    """Числа как значения, а не как строки.

    Разделители разрядов в двух языках разные, и сравнивать написание бессмысленно:
    «1 400» и «1,400» — одно число, а «3,1» и «3.1» — тоже.
    """
    cleaned = re.sub(r"(?<=\d)[\s  ](?=\d)", "", text)
    if language == "en":
        cleaned = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", cleaned)
    found: set[float] = set()
    for token in re.findall(r"\d+(?:[.,]\d+)?", cleaned):
        try:
            found.add(float(token.replace(",", ".")))
        except ValueError:
            continue
    return found


#: Числительные словами и единицы, которые при переводе естественно становятся
#: цифрой. «Волна из сорока клиентов» → "a wave of 40", «первые сутки» → "the first
#: 24 hours" — это верный перевод, а не выдуманная цифра. Ключ сравнивается как
#: префикс, поэтому падежи покрываются одной записью.
_SPELLED_OUT = {
    "один": 1, "одн": 1, "два": 2, "две": 2, "двум": 2, "двух": 2, "три": 3, "трём": 3,
    "трех": 3, "трёх": 3, "четыр": 4, "пят": 5, "шест": 6, "сем": 7, "восем": 8,
    "восьм": 8, "девят": 9, "десят": 10, "одиннадцат": 11, "двенадцат": 12,
    "тринадцат": 13, "четырнадцат": 14, "пятнадцат": 15, "шестнадцат": 16,
    "семнадцат": 17, "восемнадцат": 18, "девятнадцат": 19, "двадцат": 20,
    "тридцат": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
    "восемьдесят": 80, "девяност": 90, "сто": 100, "сот": 100, "тысяч": 1000,
    "миллион": 1000000, "миллиард": 1000000000,
    # Порядковые: «первые сутки» → "the first 24 hours".
    "перв": 1, "втор": 2, "трет": 3, "четвёрт": 4, "четверт": 4,
    # Собирательные: «четверо ушли» → "four left" или "4 left".
    "двое": 2, "трое": 3, "четверо": 4, "пятеро": 5, "шестеро": 6, "семеро": 7,
    "оба": 2, "обе": 2, "дюжин": 12,
    # Кратные и доли: «платят втрое больше» → "pay 3 times more», «треть» → "a third".
    "вдво": 2, "втро": 3, "вчетверо": 4, "впятеро": 5, "вшестеро": 6, "вдесятеро": 10,
    "половин": 2, "полутор": 1.5,
    # Единицы, у которых английский эквивалент — число.
    "сутк": 24, "суток": 24, "полчаса": 30, "квартал": 3, "полугод": 6,
}


#: Нумерованный список, у которого импортёр съел первый маркер: текст начинается
#: содержанием первого пункта, а дальше идут «2.», «3.». Английский перевод
#: восстанавливает «1.» — и это вернее оригинала, а не выдуманная цифра.
_STRIPPED_LIST_MARKER = re.compile(r"(?<!\d)2[.)]\s")


def _implied_numbers(text: str) -> set[float]:
    """Числа, которые в русском тексте написаны словом, а не цифрой.

    Словарь намеренно щедрый: лишняя запись только *разрешает* число в переводе и
    ничего не отклоняет, а недостающая стоит отклонённого файла. Ошибаться здесь
    безопаснее в сторону широты.
    """
    found: set[float] = set()
    if _STRIPPED_LIST_MARKER.search(text):
        found.add(1.0)
    for word in re.findall(r"[а-яё]+", text.lower()):
        for prefix, value in _SPELLED_OUT.items():
            if word.startswith(prefix):
                found.add(float(value))
                break
    return found


def _term_ids(text: str) -> set[str]:
    return set(_TERM.findall(text))


def field_problems(russian: str, english: Any, limit: int | None = None) -> list[str]:
    """Претензии к одному полю. Пустой список — поле переведено верно."""
    if not isinstance(english, str) or not english.strip():
        return ["пусто"]

    problems: list[str] = []
    if limit and len(english) > limit:
        # Английский бывает длиннее русского, а схема контента ограничивает поле.
        # Без этой проверки перевод молча ломает `validate_content`.
        problems.append(f"длиннее предела на {len(english) - limit} символов (можно {limit})")
    if CYRILLIC.search(english):
        problems.append("осталась кириллица")

    source_numbers = _numbers(russian, "ru")
    lost = source_numbers - _numbers(english, "en")
    if lost:
        problems.append(f"потеряны числа {sorted(lost)[:4]}")

    # Выдуманное число ищем только там, где в исходнике цифры уже есть. Абзац без
    # цифр — это проза, и число в переводе почти всегда либо числительное словом,
    # либо единица вроде «суток». Подделанная статистика опасна именно рядом с
    # настоящими цифрами — там проверка остаётся строгой.
    if source_numbers:
        invented = _numbers(english, "en") - source_numbers - _implied_numbers(russian)
        if invented:
            problems.append(f"придуманы числа {sorted(invented)[:4]}")

    if _term_ids(russian) != _term_ids(english):
        problems.append("сбита разметка терминов")
    return problems


def failing_paths(
    source: dict[str, str],
    translated: dict[str, Any],
    document: dict[str, Any] | None = None,
    limits: dict[str, int] | None = None,
) -> set[str]:
    """Какие именно поля переведены плохо.

    Нужно, чтобы переспрашивать модель только про них, а не про весь пакет: одно
    спорное поле не должно стоить трёх запросов из суточных двадцати.
    """
    caps = limits or {}
    bad = {
        path
        for path, russian in source.items()
        if field_problems(russian, translated.get(path), caps.get(path))
    }
    if document is not None:
        bad |= _mismatched_acceptance(source, translated, document)
    return bad


def _mismatched_acceptance(
    source: dict[str, str], translated: dict[str, Any], document: dict[str, Any]
) -> set[str]:
    """Эталон и варианты выбора, которые перестали совпадать.

    Возвращает **и то и другое**: переспрашивать один эталон бессмысленно, модель
    не видит вариантов, с которыми он обязан совпасть, и подгоняет наугад.
    """
    bad: set[str] = set()
    for index, item in enumerate(document.get("inputs") or []):
        choices = item.get("choices") or []
        if not choices:
            continue
        choice_paths = [f"inputs/{index}/choices/{n}" for n in range(len(choices))]
        translated_choices = {translated.get(path) for path in choice_paths}
        for rule_index, rule in enumerate(document.get("acceptance") or []):
            if rule.get("inputId") != item.get("id") or "expected" not in rule:
                continue
            expected_path = f"acceptance/{rule_index}/expected"
            expected = translated.get(expected_path)
            if expected is not None and expected not in translated_choices:
                bad.add(expected_path)
                bad.update(path for path in choice_paths if path in source)
    return bad


def validate(
    source: dict[str, str],
    translated: dict[str, Any],
    document: dict[str, Any] | None = None,
    limits: dict[str, int] | None = None,
) -> list[str]:
    """Возвращает список претензий. Пустой список — перевод можно класть в контент."""
    problems: list[str] = []

    extra = sorted(set(translated) - set(source))
    if extra:
        problems.append(f"лишние поля: {extra[:6]}")

    caps = limits or {}
    for path, russian in source.items():
        for problem in field_problems(russian, translated.get(path), caps.get(path)):
            problems.append(f"{path}: {problem}")

    if document is not None:
        problems += _exercise_problems(source, translated, document)
    return problems[:12]


def _exercise_problems(
    source: dict[str, str], translated: dict[str, Any], document: dict[str, Any]
) -> list[str]:
    """Эталон приёмки обязан остаться одним из вариантов выбора.

    `tests/test_system_design.py` отправляет каждый эталон обратно и требует, чтобы
    упражнение его приняло. Если перевод разведёт эталон и вариант, тест упадёт —
    но человеку это увидится как «правильный ответ засчитан неправильно».
    """
    if "acceptance" not in document or "inputs" not in document:
        return []
    problems = []
    for index, item in enumerate(document.get("inputs") or []):
        choices = item.get("choices") or []
        if not choices:
            continue
        translated_choices = {
            translated.get(f"inputs/{index}/choices/{choice_index}")
            for choice_index in range(len(choices))
        }
        for acceptance_index, rule in enumerate(document.get("acceptance") or []):
            if rule.get("inputId") != item.get("id") or "expected" not in rule:
                continue
            expected = translated.get(f"acceptance/{acceptance_index}/expected")
            if expected is not None and expected not in translated_choices:
                problems.append(
                    f"acceptance/{acceptance_index}: эталон «{expected}» не совпал "
                    "ни с одним переведённым вариантом"
                )
    return problems


def parse(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\s*|\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError("translation_not_json", str(exc)[:200], retryable=True) from exc
    if not isinstance(payload, dict):
        raise ProviderError("translation_not_object", "ожидался объект", retryable=True)
    return payload


def _call(system: str, prompt: str, log, model: str | None = None) -> tuple[str, str]:
    """Вызов провайдера с повтором на временных сбоях.

    Исчерпанная суточная квота сюда не попадает: она не `ProviderError`, и
    повторять её бессмысленно — прогон обязан остановиться.
    """
    from app.ai.providers import gemini_text

    last: ProviderError | None = None
    for attempt in range(1, PROVIDER_ATTEMPTS + 1):
        try:
            return gemini_text(
                system,
                prompt,
                model=model,
                max_output_tokens=32768,
                temperature=0.3,
                # Пакет на 24 000 знаков модель пишет дольше, чем оценку одной
                # попытки: общий таймаут оценщика здесь мал, и ответ обрывался.
                timeout=300.0,
            )
        except ProviderError as error:
            if not error.retryable:
                raise
            last = error
            if attempt < PROVIDER_ATTEMPTS:
                delay = PROVIDER_BACKOFF_SECONDS * (2 ** (attempt - 1))
                if log:
                    log(f"провайдер не ответил ({error.code}), повтор через {delay:.0f} с")
                time.sleep(delay)
    raise last  # type: ignore[misc]


def translate_fields(
    fields: dict[str, str],
    *,
    document: dict[str, Any] | None = None,
    limits: dict[str, int] | None = None,
    model: str | None = None,
    log=None,
) -> tuple[dict[str, str], str, list[str]]:
    """Переводит пакет полей. Возвращает (перевод, id модели, оставшиеся претензии).

    Повтор идёт **только по спорным полям**, а не по всему пакету: одно поле,
    которое модель упорно переводит не так, не должно стоить трёх запросов из
    суточных двадцати.

    Непрошедшие поля возвращаются как претензии, а не исключением: остальные
    переведены верно, и выбрасывать их вместе с одним спорным — чистая потеря.
    Решение, что делать с частичным результатом, принимает вызывающий.
    """
    # Разные модели держат разный объём вывода, и заранее он неизвестен. Ответ,
    # не поместившийся целиком, — это не брак перевода, а слишком большой пакет:
    # делим пополам и переводим половины.
    if len(fields) > 1:
        try:
            return _attempt_batch(fields, document, limits, model, log)
        except ProviderError as error:
            if error.code not in _TOO_BIG:
                raise
            if log:
                log(f"пакет не поместился в ответ ({len(fields)} полей), делю пополам")

        keys = list(fields)
        half = len(keys) // 2
        merged: dict[str, str] = {}
        problems: list[str] = []
        model_id = ""
        for part_keys in (keys[:half], keys[half:]):
            part, model_id, part_problems = translate_fields(
                {key: fields[key] for key in part_keys},
                document=document,
                limits=limits,
                model=model,
                log=log,
            )
            merged.update(part)
            problems += part_problems
        return merged, model_id, problems

    return _attempt_batch(fields, document, limits, model, log)


#: Коды, которые означают «ответ не поместился», а не «перевод плохой».
_TOO_BIG = {"provider_output_truncated", "translation_not_json"}


def _attempt_batch(
    fields: dict[str, str],
    document: dict[str, Any] | None,
    limits: dict[str, int] | None,
    model: str | None,
    log,
) -> tuple[dict[str, str], str, list[str]]:
    result: dict[str, str] = {}
    pending = dict(fields)
    problems: list[str] = []
    model_id = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        note = ""
        if problems:
            note = "The previous attempt was rejected: " + "; ".join(problems[:6]) + ". Fix it."
        raw, model_id = _call(SYSTEM_PROMPT, user_prompt(pending, note), log, model)
        for key, value in parse(raw).items():
            if key in pending and isinstance(value, str):
                result[key] = value

        problems = validate(fields, result, document, limits)
        if not problems:
            return {key: result[key] for key in fields}, model_id, []

        bad = failing_paths(fields, result, document, limits)
        if not bad:
            break
        pending = {key: fields[key] for key in bad}
        if log:
            log(f"попытка {attempt}: спорных полей {len(bad)} — {'; '.join(problems[:2])}")

    return result, model_id, problems
