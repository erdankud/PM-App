# -*- coding: utf-8 -*-
"""Аудиообзор урока: разговор двух ведущих, синтез Piper, кэш на диске.

Это не чтение урока вслух. Сценарий — диалог, написанный по тексту урока
(`app/services/audio_script.py`) и лежащий рядом с ним как контент; здесь он
только озвучивается. Разделение важное: что сказано — вопрос авторства и
проверяется отдельно, а этот модуль отвечает за то, как это звучит.

Два говорящих — два голоса. Ведущий и эксперт не должны звучать одинаково,
иначе на слух диалог снова превращается в поток текста.

Синтез детерминирован, поэтому результат кэшируется по хешу сценария: не менялся
— файл не пересчитывается, изменили — старый файл перестаёт совпадать по имени.
Ключа и сети не нужно: Piper работает локально, на CPU.

То, что нельзя произнести, не произносится: таблица становится отсылкой к экрану,
а латинские аббревиатуры проходят через словарь произношения — русский голос
читает `SLA` как «сла».
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

from app import tree_content
from app.config import settings
from app.services.glossary import describe_diagram

# Роли закреплены за голосами на весь корпус: если ведущий в одном уроке звучит
# одним голосом, а в другом другим, слушатель каждый раз заново решает, кто говорит.
VOICES = {
    "guide": "ru-RU-SvetlanaNeural",
    "expert": "ru-RU-DmitryNeural",
}

# Паузы в миллисекундах. В разговоре границы проходят не по абзацам, а по смене
# говорящего: подхват реплики короче, чем пауза перед сменой темы.
PAUSE_SAME_SPEAKER = 180
PAUSE_TURN = 380

# Шесть секций System Design в аудио объявляются вслух: на экране структура видна,
# в наушниках — нет, и без объявления непонятно, где кончился пример.
SECTION_LEADS = {
    "question": "Вопрос.",
    "cost": "Чего это стоит.",
    "substance": "Суть.",
    "example": "Пример.",
    "limits": "Границы.",
    "takeaway": "Вывод.",
}

CALLOUT_LEADS = {"info": "Обратите внимание.", "warning": "Осторожно.", "limit": "Граница."}

# Латиница в русском голосе читается через espeak как попало: `SLA` звучит как
# «сла», `RPS` — как «рпс». Словарь покрывает то, что реально встречается в
# корпусе; всё остальное espeak транслитерирует сносно.
PRONUNCIATION = {
    "API": "апи́", "AI": "эй ай", "SDK": "эс ди кей", "SMS": "эс эм эс",
    "SLA": "эс эл эй", "SLO": "эс эл о", "SLI": "эс эл ай",
    "RPO": "эр пи о", "RTO": "эр ти о", "RPS": "эр пи эс",
    "TTL": "ти ти эл", "TTFT": "ти ти эф ти", "RAG": "рэг",
    "CDN": "си ди эн", "REST": "рест", "CRM": "си эр эм",
    "LTV": "эл ти ви", "CAC": "как", "DAU": "да́у", "MAU": "ма́у",
    "DoD": "ди о ди", "UUID": "ю ю ай ди", "JSON": "джейсо́н",
    "B2B": "би ту би", "B2C": "би ту си", "MVP": "эм ви пи",
    "QA": "кью эй", "UX": "ю экс", "UI": "ю ай", "IP": "ай пи",
    "SOC": "сок", "EXIF": "экзи́ф", "Wi-Fi": "вай-фай",
    "p50": "пятидесятый перцентиль", "p95": "девяносто пятый перцентиль",
    "p99": "девяносто девятый перцентиль",
    "A/B": "эй би", "RICE": "райс", "HEART": "харт", "SCAMPER": "скампер",
    "Reach": "рич", "Impact": "импа́кт", "Confidence": "ко́нфиденс", "Effort": "э́ффорт",
    "Story": "сто́ри", "Map": "мэп", "Mapping": "мэ́ппинг", "Canvas": "ка́нвас",
    "Excel": "эксе́ль", "Android": "андро́ид", "iOS": "ай о эс",
    "retention": "ретеншн", "Retention": "ретеншн",
}


# Знаки, у которых есть звучание. Читатель видит «≈ 250 тыс.» и слышит внутри себя
# «примерно», espeak же читает символ как придётся или молчит.
SYMBOLS = {
    "≈": " примерно ", "≥": " не меньше ", "≤": " не больше ", "±": " плюс-минус ",
    "×": " умножить на ", "÷": " делить на ", "=": " равно ", "≠": " не равно ",
    "<": " меньше ", ">": " больше ", "+": " плюс ", "−": " минус ",
    "~": " примерно ", "₽": " рублей", "№": " номер ", "–": "—",
    "“": "«", "”": "»", "„": "«", '"': "",
}


def _pronounce(text: str) -> str:
    """Подставляет произношение для латинских терминов по границам слова."""
    for term in sorted(PRONUNCIATION, key=len, reverse=True):
        text = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            PRONUNCIATION[term],
            text,
        )
    return text


def _speakable(text: str, pronounce: bool = True) -> str:
    """Убирает разметку, которую видно глазом и не слышно ухом.

    `pronounce=False` оставляет термины как есть: так текст уходит в промпт
    сценаристу, которому «эс эл эй» вместо `SLA` только мешает.
    """
    text = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", text)  # термин глоссария
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)[`*_]([^`*_]+)[`*_](?!\w)", r"\1", text)
    text = text.replace("`", " ").replace("→", " ведёт к ")
    text = re.sub(r"[*_]{1,2}(?=\S)|(?<=\S)[*_]{1,2}", "", text)
    for symbol, spoken in SYMBOLS.items():
        text = text.replace(symbol, spoken)
    text = re.sub(r"\s+", " ", text).strip()
    return _pronounce(text) if pronounce else text


def _sentence(text: str) -> str:
    """Реплика без точки на конце сливается со следующей — здесь это слышно."""
    text = text.strip()
    return text if not text or text[-1] in ".!?:;»…" else text + "."


def _block_lines(block: dict, pronounce: bool = True) -> Iterator[str]:
    def _sp(value: str) -> str:
        return _speakable(value, pronounce)

    kind = block["type"]
    if kind == "paragraph":
        yield _sp(block["text"])
    elif kind == "list":
        ordered = block.get("ordered")
        for index, item in enumerate(block["items"], start=1):
            prefix = f"{index}. " if ordered else ""
            yield prefix + _sentence(_sp(item))
    elif kind == "example":
        yield _sentence(_sp(block["title"]))
        yield _sp(block["text"])
    elif kind == "model_card":
        yield _sentence(_sp(block["title"]))
        if block.get("subtitle"):
            yield _sentence(_sp(block["subtitle"]))
        for item in block["items"]:
            yield _sentence(_sp(item))
    elif kind == "callout":
        lead = CALLOUT_LEADS.get(block.get("tone", "info"), "")
        title = _sentence(_sp(block["title"])) if block.get("title") else ""
        yield " ".join(part for part in (lead, title) if part)
        yield _sp(block["text"])
    elif kind == "table":
        # Таблица вслух — это перечисление ячеек, которое невозможно удержать в голове.
        yield "Дальше в уроке таблица — её лучше посмотреть на экране."
    elif kind == "diagram_ref":
        diagram = tree_content.diagram(block["diagramId"])
        if diagram is not None:
            yield _sp(describe_diagram(diagram))
    # code опускается намеренно: идентификаторы вслух — шум, а не содержание


def block_lines_for_prompt(lesson: dict) -> list[str]:
    """Текст урока для промпта: разметка снята, произношение не подставлено.

    Сценаристу нужен урок таким, каким его читает человек. Подстановки вроде
    «эс эл эй» здесь только сбили бы модель и просочились бы в диалог.
    """
    lines: list[str] = []
    blocks = (
        [b for section in lesson["sections"] for b in section["blocks"]]
        if lesson.get("sections")
        else lesson.get("blocks", [])
    )
    for block in blocks:
        for line in _block_lines(block, pronounce=False):
            lines.append(line)
    return [line for line in lines if line]


def source_digest(lesson: dict) -> str:
    """Отпечаток текста урока: по нему видно, что сценарий отстал от урока."""
    payload = "\n".join(
        [lesson.get("title", ""), lesson.get("keyTakeaway", "")] + block_lines_for_prompt(lesson)
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def script_path(lesson: dict) -> Path:
    kind = tree_content.kind_of_block(lesson["blockId"]) or tree_content.DEFAULT_KIND
    directory = tree_content.TREES[kind]["dir"]
    return settings.content_dir / directory / "audio-scripts" / f"{lesson['id']}.json"


def load_script(lesson: dict) -> dict | None:
    """Сценарий обзора, если он есть и не отстал от урока.

    Расхождение отпечатка — это не ошибка, а состояние «урок переписали, обзор ещё
    нет». Возвращаем None, и урок живёт без аудио, пока сценарий не перегенерируют.
    """
    path = script_path(lesson)
    if not path.exists():
        return None
    script = json.loads(path.read_text(encoding="utf-8"))
    if script.get("sourceDigest") != source_digest(lesson):
        return None
    return script


def dialogue_lines(script: dict) -> list[tuple[str, str, int]]:
    """Реплики как (говорящий, произносимый текст, пауза после) — для синтеза."""
    turns = script["turns"]
    lines: list[tuple[str, str, int]] = []
    for index, turn in enumerate(turns):
        following = turns[index + 1] if index + 1 < len(turns) else None
        pause = (
            PAUSE_SAME_SPEAKER
            if following is not None and following["speaker"] == turn["speaker"]
            else PAUSE_TURN
        )
        spoken = _speakable(turn["text"])
        if spoken:
            lines.append((turn["speaker"], spoken, pause))
    return lines


def script_text(lesson: dict) -> str:
    """Плоский текст обзора — для хеша и для тестов."""
    script = load_script(lesson)
    if script is None:
        return ""
    return "\n".join(f"{speaker}: {text}" for speaker, text, _ in dialogue_lines(script))


def digest(lesson: dict) -> str:
    """Отпечаток обзора и голосов: правка сценария меняет имя файла сама."""
    voices = ",".join(f"{role}={name}" for role, name in sorted(VOICES.items()))
    return hashlib.sha256(f"{voices}\n{script_text(lesson)}".encode()).hexdigest()[:12]


def has_script(lesson: dict) -> bool:
    return load_script(lesson) is not None


def audio_path(lesson: dict) -> Path:
    return Path(settings.audio_dir) / f"{lesson['id']}.{digest(lesson)}.mp3"


# --- Синтез -----------------------------------------------------------------
#
# Голоса — нейронные голоса Microsoft, те же, что читают вслух в браузере Edge.
# Синтез идёт по сети и только на этапе сборки: API раздаёт готовые файлы и никуда
# не ходит. Поэтому недоступность сервиса ломает сборку новых обзоров, но никогда —
# выдачу уже собранных.

# Чуть быстрее нейтрального: на разговорной интонации дикторский темп звучит вяло.
SPEECH_RATE = "+4%"

# Выход сервиса: MPEG-2 Layer III, 24 кГц, моно. Тишину между репликами кодируем
# ровно в этом же формате, иначе на склейке слышен щелчок.
OUTPUT_RATE = 24000
OUTPUT_BITRATE = 48


class SynthesisUnavailable(RuntimeError):
    """Синтез недоступен. Не ошибка сервера: аудио — необязательная часть урока."""


def _silence_mp3(milliseconds: int) -> bytes:
    import lameenc

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(OUTPUT_BITRATE)
    encoder.set_in_sample_rate(OUTPUT_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    samples = b"\x00\x00" * int(OUTPUT_RATE * milliseconds / 1000)
    return encoder.encode(samples) + encoder.flush()


async def _speak(text: str, voice: str) -> bytes:
    try:
        import edge_tts
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise SynthesisUnavailable(
            "edge-tts не установлен: pip install -r requirements-audio.txt"
        ) from exc

    communicate = edge_tts.Communicate(text, voice, rate=SPEECH_RATE)
    audio = bytearray()
    async for part in communicate.stream():
        if part["type"] == "audio":
            audio += part["data"]
    if not audio:
        raise SynthesisUnavailable(f"пустой ответ синтеза для «{text[:40]}…»")
    return bytes(audio)


async def _render(lines: list[tuple[str, str, int]]) -> bytes:
    pieces: list[bytes] = []
    silences: dict[int, bytes] = {}
    for speaker, text, pause in lines:
        pieces.append(await _speak(text, VOICES[speaker]))
        if pause:
            if pause not in silences:
                silences[pause] = _silence_mp3(pause)
            pieces.append(silences[pause])
    return b"".join(pieces)


def synthesize(lesson: dict) -> Path:
    """Собирает mp3 обзора. Готовый файл возвращается как есть, без пересчёта."""
    script = load_script(lesson)
    if script is None:
        raise SynthesisUnavailable(
            f"нет сценария обзора для {lesson['id']}; "
            "сначала `python -m scripts.generate_audio_scripts`"
        )

    target = audio_path(lesson)
    if target.exists():
        return target

    mp3 = asyncio.run(_render(dialogue_lines(script)))

    target.parent.mkdir(parents=True, exist_ok=True)
    # Пишем через временный файл: прерванная сборка не должна оставить обрезанный
    # mp3, который потом раздаётся как готовый.
    temporary = target.with_suffix(".part")
    temporary.write_bytes(mp3)
    temporary.replace(target)
    return target


# Темп речи голосов, слов в минуту. Измерен на собранном файле, а не взят из
# справочника: со «150 словами в минуту» оценка врёт на четверть. Величина зависит
# от голосов и от SPEECH_RATE, поэтому при их смене её надо перемерить.
WORDS_PER_MINUTE = 110


def duration_seconds(lesson: dict) -> int:
    """Оценка длительности без синтеза — для карточки урока до загрузки файла.

    Это именно оценка: точную длительность плеер берёт из самого файла, когда тот
    скачан. Нужна она для одной строки под кнопкой, чтобы человек заранее знал,
    десять это минут или две.
    """
    script = load_script(lesson)
    if script is None:
        return 0
    lines = dialogue_lines(script)
    words = sum(len(text.split()) for _, text, _ in lines)
    pauses = sum(pause for _, _, pause in lines) / 1000
    return round(words / WORDS_PER_MINUTE * 60 + pauses)
