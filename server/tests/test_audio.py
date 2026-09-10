"""Аудиоверсия урока.

Проверяется то, что делает её честной: сценарий собирается из авторского текста и
ничего к нему не добавляет, разметка не читается вслух, а урок без готового файла
не обещает плеер.
"""

from __future__ import annotations

import re

from conftest import onboard

from app import tree_content
from app.services import audio, audio_script


def test_dialogue_never_invents_numbers_or_terms():
    """Главная гарантия обзора: разговор свой, факты — урока.

    Слова в обзоре новые по замыслу: это пересказ живой речью, а не чтение вслух.
    Проверять поэтому надо не лексику, а факты — числа и латинские термины. Курс,
    в котором ведущий округлил цифру или придумал аббревиатуру, учит выдуманному.
    """
    checked = stubs = 0
    for kind in tree_content.KINDS:
        for lesson in tree_content.tree_content(kind)["lessons"].values():
            script = audio.load_script(lesson)
            if script is None:
                continue
            if script["generator"]["provider"] == "mock":
                # Заглушка разговором не является и проверку не проходит — этим
                # и занят следующий тест. Публиковаться она не может.
                stubs += 1
                continue
            problems = audio_script.validate_script(script["turns"], lesson)
            assert not problems, f"{lesson['id']}: {problems}"
            checked += 1
    assert checked or stubs, "нет ни одного сценария обзора — проверять нечего"


def test_stub_overviews_are_never_publishable():
    """`--mock` нужен, чтобы прогнать конвейер без ключа, и только для этого.

    Заглушка раздаёт абзацы урока двум голосам, то есть делает ровно то, чем обзор
    быть не должен. Проверка обязана её отклонять — иначе она однажды уедет в релиз.
    """
    lesson = tree_content.lesson("ds1-n1-l1")
    problems = audio_script.validate_script(audio_script.mock_turns(lesson), lesson)
    assert problems, "заглушка прошла проверку — значит проверка ничего не значит"


def test_validator_catches_an_invented_number():
    """Тест на сам проверяльщик: без этого предыдущий тест ничего не значит."""
    lesson = tree_content.lesson("ds1-n1-l1")
    turns = [
        {"speaker": "guide", "text": "И насколько это дорого?"},
        {"speaker": "expert", "text": "Миграция 999 миллионов записей, вот насколько."},
    ]
    problems = audio_script.validate_script(turns, lesson)
    assert any("числа" in problem for problem in problems), problems


def test_validator_catches_an_invented_term():
    lesson = tree_content.lesson("ds1-n1-l1")
    turns = [
        {"speaker": "guide", "text": "А что с этим делать?"},
        {"speaker": "expert", "text": "Тут выручает GraphQL, как обычно."},
    ]
    assert any("термины" in p for p in audio_script.validate_script(turns, lesson))


def test_validator_rejects_a_monologue_and_a_read_aloud():
    """Один говорящий — не разговор; дословный абзац — озвученный текст."""
    lesson = tree_content.lesson("ds1-n1-l1")
    solo = [{"speaker": "expert", "text": "Так и живём."}] * 8
    assert any("разговор" in p for p in audio_script.validate_script(solo, lesson))

    quoted = audio.block_lines_for_prompt(lesson)[0]
    turns = [
        {"speaker": "guide", "text": "С чего начнём?"},
        {"speaker": "expert", "text": quoted},
    ] * 4
    assert any("цитата" in p for p in audio_script.validate_script(turns, lesson))


def test_validator_rejects_radio_host_openings():
    """«Здравствуйте, в этом уроке...» — ровно то, чем обзор быть не должен."""
    lesson = tree_content.lesson("ds1-n1-l1")
    turns = [
        {"speaker": "guide", "text": "Здравствуйте! Сегодня мы поговорим о схемах."},
        {"speaker": "expert", "text": "Именно так."},
    ] * 3
    assert any("обороты" in p for p in audio_script.validate_script(turns, lesson))


def test_edited_lesson_invalidates_its_overview(tmp_path, monkeypatch):
    """Урок переписали — старый обзор перестаёт считаться действующим.

    Это не ошибка, а состояние «сценарий отстал»: у урока просто нет аудио, пока
    обзор не перегенерируют. Молча озвучивать прошлую редакцию — хуже.
    """
    lesson = dict(tree_content.lesson("ds1-n1-l1"))
    assert audio.load_script(lesson) is not None
    lesson["title"] = lesson["title"] + " (правка)"
    assert audio.load_script(lesson) is None


def test_markup_never_reaches_the_listener():
    """Звёздочки, обратные кавычки и идентификаторы терминов не произносятся."""
    for kind in tree_content.KINDS:
        for lesson in tree_content.tree_content(kind)["lessons"].values():
            script = audio.script_text(lesson)
            assert "[[" not in script and "`" not in script, lesson["id"]
            assert not re.search(r"\*\*|__", script), lesson["id"]
            # Символы без звучания: слушатель услышал бы пропуск или мусор.
            assert not set(script) & {"≈", "×", "≥", "≤", "±", "="}, lesson["id"]


def test_latin_abbreviations_are_spelled_for_a_russian_voice():
    """`SLA` русским голосом читается как «сла» — словарь произношения это чинит."""
    spoken = audio._speakable("Цель по SLA и p95, отчёт в API.")
    assert "SLA" not in spoken and "p95" not in spoken and "API" not in spoken
    assert "эс эл эй" in spoken and "девяносто пятый перцентиль" in spoken


def test_both_lesson_shapes_reach_the_scriptwriter():
    """Уроки основного дерева — плоские блоки, System Design — секции."""
    product = tree_content.lesson("d1-feedback-matrix")
    assert product.get("sections") in (None, [])
    assert len(audio_script.lesson_body(product)) > 200

    sd = tree_content.lesson("ds1-n1-l1")
    assert sd["sections"]
    assert len(audio_script.lesson_body(sd)) > 200


def test_prompt_text_keeps_terms_unspoken():
    """Сценаристу урок отдаётся как есть: «эс эл эй» вместо `SLA` сбило бы его."""
    spoken = audio._speakable("Цель по SLA", pronounce=True)
    written = audio._speakable("Цель по SLA", pronounce=False)
    assert "эс эл эй" in spoken and "SLA" in written


def test_digest_changes_with_the_lesson():
    """Отпечаток — это и есть проверка свежести: правка урока обесценивает файл."""
    lesson = dict(tree_content.lesson("ds1-n1-l1"))
    before = audio.digest(lesson)
    lesson["title"] = lesson["title"] + " (правка)"
    assert audio.digest(lesson) != before


def test_lesson_without_audio_does_not_offer_a_player(client, monkeypatch, tmp_path):
    """Пустой каталог — плеера нет, и это не ошибка."""
    monkeypatch.setattr(audio.settings, "audio_dir", str(tmp_path))
    headers, _ = onboard(client)
    body = client.get("/v1/lessons/ds1-n1-l1", headers=headers).json()
    assert body["audio"]["available"] is False
    assert body["audio"]["status"] == "absent"
    assert body["audio"]["url"] is None
    assert client.get("/v1/lessons/ds1-n1-l1/audio", headers=headers).status_code == 404


def test_lesson_with_audio_serves_the_file(client, monkeypatch, tmp_path):
    """Готовый файл раздаётся как mp3, а адрес несёт отпечаток сценария."""
    monkeypatch.setattr(audio.settings, "audio_dir", str(tmp_path))
    lesson = tree_content.lesson("ds1-n1-l1")
    audio.audio_path(lesson).write_bytes(b"\xff\xfb\x90\x00fake mp3")

    headers, _ = onboard(client, language="ru")
    body = client.get("/v1/lessons/ds1-n1-l1", headers=headers).json()
    assert body["audio"]["available"] is True
    assert audio.digest(lesson) in body["audio"]["url"]
    assert body["audio"]["durationSeconds"] > 0

    served = client.get("/v1/lessons/ds1-n1-l1/audio", headers=headers)
    assert served.status_code == 200
    assert served.headers["content-type"] == "audio/mpeg"


def test_audio_requires_a_signed_in_user(client):
    """Аудио — часть урока, а урок за входом."""
    assert client.get("/v1/lessons/ds1-n1-l1/audio").status_code == 401


def test_generation_button_is_off_unless_enabled(client, monkeypatch, tmp_path):
    """В релизной сборке кнопки нет, и запуск отклоняется на сервере.

    Клиент её и не покажет, но полагаться на это нельзя: разрешение — свойство
    сервера, ровно как со статусом разблокировки блоков.
    """
    monkeypatch.setattr(audio.settings, "audio_dir", str(tmp_path))
    monkeypatch.setattr(audio.settings, "allow_audio_generation", False)
    headers, _ = onboard(client)

    body = client.get("/v1/lessons/ds1-n1-l1", headers=headers).json()
    assert body["audio"]["canGenerate"] is False

    started = client.post("/v1/lessons/ds1-n1-l1/audio/generate", headers=headers)
    assert started.status_code == 403
    assert started.json()["detail"]["code"] == "audio_generation_disabled"


def test_generation_reports_progress_without_blocking(client, monkeypatch, tmp_path):
    """Запуск отвечает «принято», а не ждёт минуту синтеза."""
    from app.services import audio_jobs

    monkeypatch.setattr(audio.settings, "audio_dir", str(tmp_path))
    monkeypatch.setattr(audio.settings, "allow_audio_generation", True)
    # Задачу не выполняем: проверяется контракт запуска, а не работа провайдера.
    monkeypatch.setattr(audio_jobs.threading, "Thread", lambda **kw: type(
        "Stub", (), {"start": lambda self: None}
    )())
    headers, _ = onboard(client)

    started = client.post("/v1/lessons/ds1-n1-l1/audio/generate", headers=headers)
    assert started.status_code == 202
    assert started.json()["status"] == "generating"

    body = client.get("/v1/lessons/ds1-n1-l1", headers=headers).json()
    assert body["audio"]["status"] == "generating"
    assert body["audio"]["available"] is False
    audio_jobs._jobs.clear()
