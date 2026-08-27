"""Аудиоверсия урока.

Проверяется то, что делает её честной: сценарий собирается из авторского текста и
ничего к нему не добавляет, разметка не читается вслух, а урок без готового файла
не обещает плеер.
"""

from __future__ import annotations

import re

from conftest import onboard

from app import tree_content
from app.services import audio


def test_script_is_assembled_from_the_authored_text_only():
    """В сценарии нет ни одного слова, которого нет в уроке.

    Это главное свойство: аудио — тот же урок вслух. Если сюда просочится
    сгенерированный текст, слушатель и читатель получат разные уроки.
    """
    lesson = tree_content.lesson("ds1-n1-l1")
    from app.services.glossary import describe_diagram

    # Авторский материал урока — его текст и структура его схем. Описание схемы
    # словами строится из той же структуры (`describe_diagram`), поэтому считается
    # авторским: там нет ничего, чего нет в самой схеме.
    # Разметка глоссария оборачивает основу слова, а окончание остаётся снаружи —
    # `[[relation|связь]]ю`. Поэтому сравнивать надо с текстом после снятия разметки,
    # то есть ровно с тем, что видит читатель.
    def shown(text: str) -> str:
        return re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", text)

    source = " ".join(
        [
            shown(block.get("text", "") + " ".join(block.get("items", [])))
            for section in lesson["sections"]
            for block in section["blocks"]
        ]
        + [describe_diagram(tree_content.diagram(d)) for d in lesson.get("diagramIds", [])]
    ).lower()

    # Служебные слова, которые добавляет сама озвучка: названия секций и отсылки
    # к экрану. Их список закрыт и лежит в модуле — выдумать реплику нельзя.
    spoken_frames = {
        word
        for phrase in list(audio.SECTION_LEADS.values())
        + list(audio.CALLOUT_LEADS.values())
        + ["Дальше в уроке таблица — её лучше посмотреть на экране.", lesson["title"]]
        for word in re.findall(r"\w+", phrase.lower())
    }
    spoken_frames |= {w for phrase in audio.PRONUNCIATION.values() for w in phrase.lower().split()}
    spoken_frames |= {w for phrase in audio.SYMBOLS.values() for w in phrase.lower().split()}
    spoken_frames |= {"схема", "элементы", "связи", "ведёт", "к"}

    unknown = [
        word
        for word in re.findall(r"[а-яё]+", audio.script_text(lesson).lower())
        if word not in source and word not in spoken_frames
    ]
    assert not unknown, f"в озвучке появились слова, которых нет в уроке: {unknown[:10]}"


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


def test_both_lesson_shapes_produce_a_script():
    """Уроки основного дерева — плоские блоки, System Design — секции."""
    product = tree_content.lesson("d1-feedback-matrix")
    assert product.get("sections") in (None, [])
    script = audio.script_text(product)
    assert product["keyTakeaway"][:40] in script
    assert product["checkQuestion"][:40] in script

    sd = tree_content.lesson("ds1-n1-l1")
    assert sd["sections"]
    assert "Вывод." in audio.script_text(sd)


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
    assert body["audio"] == {"available": False, "url": None, "durationSeconds": None}
    assert client.get("/v1/lessons/ds1-n1-l1/audio", headers=headers).status_code == 404


def test_lesson_with_audio_serves_the_file(client, monkeypatch, tmp_path):
    """Готовый файл раздаётся как mp3, а адрес несёт отпечаток сценария."""
    monkeypatch.setattr(audio.settings, "audio_dir", str(tmp_path))
    lesson = tree_content.lesson("ds1-n1-l1")
    audio.audio_path(lesson).write_bytes(b"\xff\xfb\x90\x00fake mp3")

    headers, _ = onboard(client)
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
