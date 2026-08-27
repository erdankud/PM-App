# -*- coding: utf-8 -*-
"""Аудиоверсия урока: сценарий из авторских секций, синтез Piper, кэш на диске.

Сценарий здесь **собирается, а не пишется**: текст берётся из тех же секций, что
человек видит на экране, и порядок фиксирован. Поэтому аудио — это тот же урок,
прочитанный вслух, а не пересказ, который может разойтись с оригиналом.

Из этого следует остальное устройство. Синтез детерминирован, значит результат
кэшируется по хешу сценария: урок не менялся — файл не пересчитывается, урок
изменили — старый файл перестаёт совпадать по имени и его место занимает новый.
Ключа и сети не нужно вовсе: Piper работает локально, на CPU, примерно в 25 раз
быстрее реального времени.

То, что нельзя прочитать вслух, не читается. Таблица голосом превращается в
перечисление ячеек, поэтому вместо неё звучит отсылка к экрану. Схема, наоборот,
читается: `describe_diagram` уже строит её описание словами для VoiceOver.
"""

from __future__ import annotations

import hashlib
import re
import wave
from pathlib import Path
from typing import Iterator

from app import tree_content
from app.config import settings
from app.services.glossary import describe_diagram

VOICE = "ru_RU-irina-medium"
SAMPLE_RATE_FALLBACK = 22050
BIT_RATE = 48

# Пауза после реплики, в миллисекундах. Слушателю нужна граница там, где читателю
# хватает пустой строки: на слух абзацы иначе слипаются в один поток.
PAUSE_BLOCK = 350
PAUSE_SECTION = 750

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


def _speakable(text: str) -> str:
    """Убирает разметку, которую видно глазом и не слышно ухом."""
    text = re.sub(r"\[\[[^|\]]*\|([^\]]+)\]\]", r"\1", text)  # термин глоссария
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)[`*_]([^`*_]+)[`*_](?!\w)", r"\1", text)
    text = text.replace("`", " ").replace("→", " ведёт к ")
    text = re.sub(r"[*_]{1,2}(?=\S)|(?<=\S)[*_]{1,2}", "", text)
    for symbol, spoken in SYMBOLS.items():
        text = text.replace(symbol, spoken)
    return _pronounce(re.sub(r"\s+", " ", text).strip())


def _sentence(text: str) -> str:
    """Реплика без точки на конце сливается со следующей — здесь это слышно."""
    text = text.strip()
    return text if not text or text[-1] in ".!?:;»…" else text + "."


def _block_lines(block: dict) -> Iterator[str]:
    kind = block["type"]
    if kind == "paragraph":
        yield _speakable(block["text"])
    elif kind == "list":
        ordered = block.get("ordered")
        for index, item in enumerate(block["items"], start=1):
            prefix = f"{index}. " if ordered else ""
            yield prefix + _sentence(_speakable(item))
    elif kind == "example":
        yield _sentence(_speakable(block["title"]))
        yield _speakable(block["text"])
    elif kind == "model_card":
        yield _sentence(_speakable(block["title"]))
        if block.get("subtitle"):
            yield _sentence(_speakable(block["subtitle"]))
        for item in block["items"]:
            yield _sentence(_speakable(item))
    elif kind == "callout":
        lead = CALLOUT_LEADS.get(block.get("tone", "info"), "")
        title = _sentence(_speakable(block["title"])) if block.get("title") else ""
        yield " ".join(part for part in (lead, title) if part)
        yield _speakable(block["text"])
    elif kind == "table":
        # Таблица вслух — это перечисление ячеек, которое невозможно удержать в голове.
        yield "Дальше в уроке таблица — её лучше посмотреть на экране."
    elif kind == "diagram_ref":
        diagram = tree_content.diagram(block["diagramId"])
        if diagram is not None:
            yield _speakable(describe_diagram(diagram))
    # code опускается намеренно: идентификаторы вслух — шум, а не содержание


def narration_script(lesson: dict) -> list[tuple[str, int]]:
    """Сценарий как список реплик с паузой после каждой.

    Возвращается структурой, а не строкой, потому что паузу между секциями нельзя
    выразить пунктуацией: точка даёт около ста миллисекунд, а границе раздела
    нужно почти секунда.
    """
    lines: list[tuple[str, int]] = [
        (_sentence(_speakable(lesson["title"])), PAUSE_SECTION),
    ]

    if lesson.get("sections"):
        for section in lesson["sections"]:
            lead = SECTION_LEADS.get(section.get("kind", ""))
            if lead:
                lines.append((lead, PAUSE_BLOCK))
            blocks = section["blocks"]
            for index, block in enumerate(blocks):
                pause = PAUSE_SECTION if index == len(blocks) - 1 else PAUSE_BLOCK
                for line in _block_lines(block):
                    lines.append((line, pause))
    else:
        for block in lesson.get("blocks", []):
            for line in _block_lines(block):
                lines.append((line, PAUSE_BLOCK))
        if lesson.get("keyTakeaway"):
            lines.append(("Главное.", PAUSE_BLOCK))
            lines.append((_speakable(lesson["keyTakeaway"]), PAUSE_SECTION))
        if lesson.get("checkQuestion"):
            lines.append(("И вопрос, чтобы проверить себя.", PAUSE_BLOCK))
            lines.append((_speakable(lesson["checkQuestion"]), PAUSE_SECTION))

    return [(text, pause) for text, pause in lines if text]


def script_text(lesson: dict) -> str:
    """Плоский текст сценария — для хеша, тестов и субтитров."""
    return "\n".join(text for text, _ in narration_script(lesson))


def digest(lesson: dict) -> str:
    """Отпечаток сценария и голоса: урок изменили — имя файла меняется само."""
    payload = f"{VOICE}\n{script_text(lesson)}".encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def audio_path(lesson: dict) -> Path:
    return Path(settings.audio_dir) / f"{lesson['id']}.{digest(lesson)}.mp3"


# --- Синтез -----------------------------------------------------------------
#
# Piper импортируется лениво: он тянет onnxruntime, а API, который только раздаёт
# готовые файлы, не должен от этого зависеть. Если голоса нет — урок просто живёт
# без аудио, и это не ошибка.

_voice = None


class VoiceUnavailable(RuntimeError):
    """Голос не установлен. Не ошибка сервера: аудио — необязательная часть урока."""


def voice_model_path() -> Path:
    return Path(settings.audio_voice_dir) / f"{VOICE}.onnx"


def voice_available() -> bool:
    return voice_model_path().exists()


def _load_voice():
    global _voice
    if _voice is None:
        if not voice_available():
            raise VoiceUnavailable(
                f"нет голоса {VOICE} в {settings.audio_voice_dir}; "
                "поставьте его через `python -m scripts.build_audio --download`"
            )
        try:
            from piper import PiperVoice
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise VoiceUnavailable("piper-tts не установлен") from exc
        _voice = PiperVoice.load(str(voice_model_path()))
    return _voice


def _silence(milliseconds: int, rate: int) -> bytes:
    return b"\x00\x00" * int(rate * milliseconds / 1000)


def synthesize(lesson: dict) -> Path:
    """Собирает mp3 урока. Готовый файл возвращается как есть, без пересчёта."""
    target = audio_path(lesson)
    if target.exists():
        return target

    import lameenc

    voice = _load_voice()
    rate = getattr(getattr(voice, "config", None), "sample_rate", SAMPLE_RATE_FALLBACK)

    pcm = bytearray()
    for text, pause in narration_script(lesson):
        for chunk in voice.synthesize(text):
            pcm += chunk.audio_int16_bytes
        pcm += _silence(pause, rate)

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(BIT_RATE)
    encoder.set_in_sample_rate(rate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    mp3 = encoder.encode(bytes(pcm)) + encoder.flush()

    target.parent.mkdir(parents=True, exist_ok=True)
    # Пишем через временный файл: два одновременных запроса на один урок не должны
    # оставить после себя обрезанный mp3, который потом раздаётся как готовый.
    temporary = target.with_suffix(".part")
    temporary.write_bytes(mp3)
    temporary.replace(target)
    return target


# Темп речи голоса, слов в минуту. Не взят из головы: измерен по 112 собранным
# файлам (медиана). Со справочными «150 слов в минуту» оценка врала на четверть, и
# на карточке урока стояло «4:21» там, где звучало 5:24.
WORDS_PER_MINUTE = 114


def duration_seconds(lesson: dict) -> int:
    """Оценка длительности без синтеза — для карточки урока до загрузки файла.

    Это именно оценка: точную длительность плеер берёт из самого файла, когда тот
    скачан. Нужна она для одной строки под кнопкой, чтобы человек заранее знал,
    десять это минут или две.
    """
    words = len(script_text(lesson).split())
    pauses = sum(pause for _, pause in narration_script(lesson)) / 1000
    return round(words / WORDS_PER_MINUTE * 60 + pauses)
