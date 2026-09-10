"""Interface language and the language coaching is written in.

Content itself is authored in the content language now rather than translated at
request time (spec v0.2 §16), so what is tested here is the machinery that still
carries a choice: server-owned copy, the derived vocabularies, and the language the
evaluator is told to write in.
"""

from __future__ import annotations

import json
import re

from conftest import onboard, read_all_lessons, start_gate

from app import tree_content
from app.i18n import Language, copy, tag_label
from app.services.scoring import score_band
from app.services.skills import label as skill_label
from app.worker import run_once

CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")


def _russian(text: str) -> bool:
    return bool(CYRILLIC.search(text or ""))


def switch(client, headers, language: str) -> dict:
    return client.patch(
        "/v1/me/profile", headers=headers, json={"language": language}
    ).json()


# --- Vocabularies ------------------------------------------------------------


def test_every_competency_has_both_languages():
    from app.models import SKILL_KEYS

    # Восемь компетенций: шесть доменов карты, communication и system_design
    # (спека v0.2 §7 плюс спека System Design §2.2).
    assert len(SKILL_KEYS) == 8
    for key in SKILL_KEYS:
        assert _russian(skill_label(key, Language.RU)), key
        assert not _russian(skill_label(key, Language.EN)), key


def test_bands_and_tags_and_copy_have_both_languages():
    assert _russian(score_band(90, Language.RU))
    assert score_band(90, Language.EN) == "Strong reasoning"
    assert _russian(tag_label("discovery", Language.RU))
    for key in ("what_good_looks_like", "progress_footnote"):
        assert _russian(copy(key, Language.RU))
        assert not _russian(copy(key, Language.EN))


def test_unknown_values_degrade_readably():
    assert Language.coerce(None) is Language.EN
    assert Language.coerce("de") is Language.EN
    assert Language.coerce("ru-RU") is Language.RU
    assert skill_label("brand_new", Language.RU) == "brand_new"
    assert tag_label("brand-new", Language.RU) == "Brand New"


# --- Authored content --------------------------------------------------------


def test_lessons_and_gate_scenarios_are_written_in_the_authored_language():
    content = tree_content.tree_content()
    assert content["lessons"], "no lessons authored"
    for lesson in content["lessons"].values():
        assert _russian(lesson["title"]), lesson["id"]
        assert _russian(lesson["keyTakeaway"]), lesson["id"]
        for block in lesson["blocks"]:
            for field in ("text", "title", "subtitle"):
                # A model card's title is the model's own name — "Feedback Matrix",
                # "5 Whys", "HEART". Those are terms of art and stay as they are.
                if field == "title" and block["type"] == "model_card":
                    continue
                if block.get(field):
                    assert _russian(block[field]), f"{lesson['id']}/{field}"
    for scenario in content["scenarios"].values():
        assert _russian(scenario["title"]), scenario["id"]
        for value in scenario["brief"].values():
            assert _russian(value), scenario["id"]
        for card in scenario["evidenceCards"]:
            assert _russian(card["content"]), f"{scenario['id']}/{card['id']}"


def test_tree_titles_are_written_in_the_authored_language():
    content = tree_content.tree_content()
    for block in content["tree"]["blocks"]:
        assert _russian(block["title"]), block["id"]
        for node in block["nodes"]:
            assert _russian(node["title"]), node["id"]
            assert _russian(node["keyQuestion"]), node["id"]


# --- API ---------------------------------------------------------------------


def test_language_persists_and_the_header_overrides_one_request(client):
    headers, me = onboard(client)
    # English until someone chooses otherwise: the corpus is authored in Russian,
    # but the product's own language is English and nobody has picked yet.
    assert me["language"] == "en"
    english = client.get("/v1/progress", headers=headers).json()
    assert not _russian(english["footnote"])
    assert not _russian(english["skills"][0]["label"])

    assert switch(client, headers, "ru")["language"] == "ru"
    russian = client.get("/v1/progress", headers=headers).json()
    assert _russian(russian["footnote"])

    # The header closes the gap between switching in the app and the PATCH landing.
    header_english = client.get(
        "/v1/progress", headers={**headers, "X-Content-Language": "en"}
    ).json()
    assert not _russian(header_english["footnote"])
    assert client.get("/v1/me", headers=headers).json()["language"] == "ru"


def test_coaching_is_written_in_the_learners_language(client):
    headers, _ = onboard(client, language="ru")
    read_all_lessons(client, headers, "D1")
    challenge = start_gate(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    for card in challenge["scenario"]["evidenceCards"]:
        client.post(
            f"/v1/attempts/{attempt_id}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )
    client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "selectedOptionId": challenge["scenario"]["decisionOptions"][0]["id"],
            "rationale": (
                "Разложу обратную связь по задаче и разрежу метрики по сегментам, "
                "потому что среднее 3,1 скрывает распределение. Компромисс в том, что "
                "я сдвину звонки на два дня. Буду измерять долю обменов без сообщения "
                "владельцу."
            ),
        },
    )
    while run_once():
        pass

    feedback = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    body = feedback["feedback"]
    assert _russian(body["band"])
    assert _russian(body["sharperApproach"])
    for point in body["strengths"] + body["improvements"]:
        assert _russian(point["title"])
        assert _russian(point["detail"])
    for impact in body["skillImpact"]:
        assert _russian(impact["label"])


def test_language_choice_does_not_change_the_score(client):
    scores = {}
    rationale = (
        "Пишут сотрудники, а платит владелец. Среднее 3,1 скрывает распределение, "
        "поэтому сначала разрежу по сегментам. Компромисс — сдвиг звонков на два дня. "
        "Измерять буду долю обменов без сообщения владельцу."
    )
    for language in ("ru", "en"):
        headers, _ = onboard(client)
        switch(client, headers, language)
        read_all_lessons(client, headers, "D1")
        challenge = start_gate(client, headers)
        attempt_id = challenge["attempt"]["attemptId"]
        for card in challenge["scenario"]["evidenceCards"]:
            client.post(
                f"/v1/attempts/{attempt_id}/evidence",
                headers=headers,
                json={"evidenceCardId": card["id"]},
            )
        client.post(
            f"/v1/attempts/{attempt_id}/submit",
            headers=headers,
            json={
                "selectedOptionId": challenge["scenario"]["decisionOptions"][0]["id"],
                "rationale": rationale,
            },
        )
        while run_once():
            pass
        scores[language] = client.get(
            f"/v1/attempts/{attempt_id}/feedback", headers=headers
        ).json()["feedback"]["score"]

    assert scores["ru"] == scores["en"]


# --- Перевод -----------------------------------------------------------------
#
# Английский корпус — наложение поверх авторского русского. Проверяется не качество
# перевода (это дело вычитки), а границы: что переводится, что нет, и не разъезжается
# ли перевод с исходником.


def test_the_rubric_is_never_translated():
    """Балл не должен зависеть от языка — и не может, потому что переводить нечего.

    Рубрика, веса вариантов и QA-фикстуры существуют в одном экземпляре: в карте
    переводимых путей их нет. Единственное исключение — `remediation.gap`, который
    видит человек после несданного гейта.
    """
    from app.i18n_content import translatable

    for kind in tree_content.KINDS:
        for scenario in tree_content.tree_content(kind)["scenarios"].values():
            for path in translatable("scenario", scenario):
                if path.startswith("rubric"):
                    assert re.fullmatch(r"rubric/remediation/\d+/gap", path), path
                assert not path.startswith("qaSubmissions"), path
                assert "rubricNote" not in path, path


def test_translations_are_current_and_complete():
    """Наполовину переведённый файл читается как поломка, а не как «ещё не перевели».

    Устаревшее наложение (урок правили после перевода) не применяется молча — здесь
    это ошибка, чтобы расхождение нашлось в CI, а не на экране.
    """
    from app.i18n_content import TRANSLATED_LANGUAGES, digest, translatable
    from scripts.translate_content import sources

    for language in TRANSLATED_LANGUAGES:
        for doc_kind, path in sources(
            list(tree_content.KINDS),
            ["tree", "lesson", "scenario", "exercise", "glossary", "diagram"],
        ):
            overlay = tree_content.overlay_path(path, language)
            if not overlay.exists():
                continue
            payload = json.loads(overlay.read_text(encoding="utf-8"))
            document = json.loads(path.read_text(encoding="utf-8"))
            assert payload["sourceDigest"] == digest(doc_kind, document), (
                f"{overlay.name}: перевод отстал от исходника"
            )
            missing = set(translatable(doc_kind, document)) - set(payload["fields"])
            assert not missing, f"{overlay.name}: не переведено {len(missing)} полей"


def test_a_translated_lesson_reads_in_english():
    """Перевод есть — значит, кириллицы в нём не осталось."""
    from app.i18n_content import translatable

    translated = [
        lesson_id
        for kind in tree_content.KINDS
        for lesson_id, lesson in tree_content.tree_content(kind, "en")["lessons"].items()
        if not _russian(lesson["title"])
    ]
    if not translated:
        return  # корпус ещё не переведён — это состояние, а не сбой

    lesson = tree_content.lesson(translated[0], "en")
    for path, value in translatable("lesson", lesson).items():
        assert not _russian(value), f"{lesson['id']}/{path}"


def test_the_authored_lesson_is_untouched_by_translation():
    """Наложение кладётся на копию: русский урок остаётся русским."""
    lesson_id = next(iter(tree_content.tree_content("product")["lessons"]))
    tree_content.lesson(lesson_id, "en")
    assert _russian(tree_content.lesson(lesson_id)["title"])


def test_the_translation_validator_guards_figures_without_crying_wolf():
    """Проверка чисел должна ловить подделку и не ловить нормальный перевод.

    Ложное срабатывание здесь стоит дорого: одна претензия отклоняет пакет из
    десяти файлов, и прогон по корпусу теряет их все.
    """
    from app.services.translation import validate

    def check(russian: str, english: str) -> list[str]:
        return validate({"a": russian}, {"a": english})

    # Числительное словом и «сутки» в переводе законно становятся цифрой.
    assert not check(
        "Волна из сорока клиентов. Первые сутки — лотерея.",
        "A wave of 40 customers. The first 24 hours are a lottery.",
    )
    assert not check("Отток вырос за две недели.", "Churn grew over 2 weeks.")
    # Разделители разрядов у языков разные, число — то же самое.
    assert not check("1 400 аккаунтов, среднее 3,1", "1,400 accounts, average 3.1")

    # Изменённая цифра — брак.
    assert check("Отток вырос с 9% до 16%.", "Churn grew from 9% to 20%.")
    # Подделанная статистика рядом с настоящей — тоже.
    assert check("Отток вырос с 9%.", "Churn grew from 9% among 3000000 users.")
    # Сбитая разметка термина уводит ссылку в никуда.
    assert check("В [[sla|SLA]] записано 99,9%", "The [[slo|SLA]] says 99.9%")


def test_a_disputed_field_is_isolated_rather_than_failing_the_batch():
    """Одно спорное поле не должно уносить с собой правильно переведённые.

    Пакет везёт около десяти файлов ради экономии запросов; если брак одного
    абзаца отклоняет весь пакет, экономия превращается в потери.
    """
    from app.services.translation import failing_paths

    source = {"a": "Отток вырос с 9% до 16%.", "b": "Волна из сорока клиентов."}
    translated = {"a": "Churn grew from 9% to 20%.", "b": "A wave of 40 customers."}

    assert failing_paths(source, translated) == {"a"}


def test_the_translation_respects_the_length_limits_of_the_schema():
    """Английский бывает длиннее русского, а схема контента ограничивает поле.

    Без этой проверки перевод молча ломает `validate_content`, и увидеть это
    можно только на следующем прогоне — когда переведены уже сотни файлов.
    """
    from app.i18n_content import max_length
    from app.services.translation import validate

    # Предел берётся из той же схемы, что проверяет авторский контент.
    assert max_length("scenario", "decisionOptions/0/consequence") == 1200
    assert max_length("scenario", "evidenceCards/2/title") == 60

    caps = {"a": 1200}
    assert validate({"a": "коротко"}, {"a": "x" * 1201}, None, caps)
    assert not validate({"a": "коротко"}, {"a": "x" * 1200}, None, caps)


def test_an_oversized_batch_is_split_rather_than_lost(monkeypatch):
    """Обрезанный по лимиту вывода ответ — это «пакет велик», а не «перевод плохой».

    Разные модели держат разный объём вывода, и заранее он неизвестен: единственный
    надёжный ответ — разделить пакет и перевести половины.
    """
    from app.ai.base import ProviderError
    from app.services import translation

    seen: list[int] = []

    def fake_call(system, prompt, log, model=None):
        import json as _json

        # Из промпта достаём, сколько полей просили: большой пакет «не влезает».
        fields = _json.loads(prompt[prompt.index("{") :])
        seen.append(len(fields))
        if len(fields) > 2:
            raise ProviderError("provider_output_truncated", "не поместилось")
        return _json.dumps({key: "Translated." for key in fields}), "test-model"

    monkeypatch.setattr(translation, "_call", fake_call)

    source = {f"f{index}": "Русский текст." for index in range(4)}
    result, _, problems = translation.translate_fields(source)

    assert not problems
    assert set(result) == set(source)
    # Сначала попробовали целиком, потом половинами.
    assert seen[0] == 4 and max(seen[1:]) <= 2


def test_length_floors_apply_to_the_author_and_ceilings_to_everyone():
    """`minLength` — правило для автора, `maxLength` — свойство продукта.

    Английский законно короче русского: «Согласиться на 99.95%. Ноль недель.» —
    35 знаков, "Agree to 99.95%. Zero weeks." — 28. Требовать от перевода добрать
    до тридцати значит просить дописать воды. Верхняя граница остаётся: текст
    обязан поместиться на экран, на каком бы языке он ни был.
    """
    authored = tree_content.gate_scenario_schema("ru")
    translated = tree_content.gate_scenario_schema("en")

    option = lambda schema: schema["properties"]["decisionOptions"]["items"]["properties"]
    assert option(authored)["description"]["minLength"] == 30
    assert "minLength" not in option(translated)["description"]
    assert option(translated)["description"]["maxLength"] == 320


CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _cyrillic_fields(payload, path=""):
    """Пути до строк с кириллицей внутри ответа."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield from _cyrillic_fields(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from _cyrillic_fields(value, f"{path}[{index}]")
    elif isinstance(payload, str) and CYRILLIC.search(payload):
        yield path, payload


def test_english_responses_carry_no_russian(client):
    """Английский экран не должен показывать русский текст.

    Это ловится только на ответе целиком: корпус может быть переведён на сто
    процентов, а строка всё равно приедет по-русски — потому что эндпоинт забыл
    передать язык вниз, или потому что поле вообще не в списке переводимых.
    Оба случая уже случались: `lessons_for_block` вызывали без языка, и названия
    моделей узлов не переводились никогда.
    """
    headers, _ = onboard(client)
    headers = {**headers, "X-Content-Language": "en"}

    payloads: dict[str, object] = {}
    for kind in ("product", "system_design"):
        payloads[f"/tree/{kind}"] = client.get(f"/v1/tree/{kind}", headers=headers).json()
        payloads[f"/tree/{kind}/map"] = client.get(
            f"/v1/tree/{kind}/map", headers=headers
        ).json()
    payloads["/trees"] = client.get("/v1/trees", headers=headers).json()
    payloads["/progress"] = client.get("/v1/progress", headers=headers).json()

    for block_id in ("D1", "G3", "DS1", "SE3"):
        block = client.get(f"/v1/blocks/{block_id}", headers=headers).json()
        payloads[f"/blocks/{block_id}"] = block
        first = block["nodes"][0]["lessons"][0]["id"]
        payloads[f"/lessons/{first}"] = client.get(
            f"/v1/lessons/{first}", headers=headers
        ).json()

    leaks = [
        f"{endpoint}{path}: {text[:60]}"
        for endpoint, payload in payloads.items()
        for path, text in _cyrillic_fields(payload)
    ]
    assert not leaks, "русский текст в английском ответе:\n" + "\n".join(leaks)


def test_russian_stays_russian(client):
    """Обратная проверка: правка выше не должна была подменить язык оригинала."""
    headers, _ = onboard(client)
    block = client.get("/v1/blocks/D1", headers={**headers, "X-Content-Language": "ru"}).json()
    titles = [lesson["title"] for node in block["nodes"] for lesson in node["lessons"]]
    assert titles and all(CYRILLIC.search(title) for title in titles)
