# -*- coding: utf-8 -*-
"""Переводит авторский корпус на другой язык.

Перевод — **наложение**: авторские файлы не трогаются, результат ложится в
`content/i18n/<язык>/` по тому же относительному пути и приезжает поверх исходника
при чтении. Ошибка в этом скрипте физически не может испортить оригинал.

    export EVALUATOR_API_KEY=...                        # ключ Google AI Studio
    python -m scripts.translate_content                 # весь корпус
    python -m scripts.translate_content --type lesson   # только уроки
    python -m scripts.translate_content --limit 5       # первые пять файлов
    python -m scripts.translate_content --only d1-five-whys
    python -m scripts.validate_content

Прогон возобновляемый: файл с актуальным отпечатком исходника пропускается, поэтому
прерванный на середине корпус дописывается тем же вызовом. Правка урока меняет
отпечаток — перевод перестаёт считаться современным и перегенерируется.

Модель проверяется, а не принимается на веру (`app/services/translation.py`):
пропущенное поле, потерянное число, сбитая разметка термина или кириллица в выводе
означают, что попытка не засчитана и повторяется с перечнем претензий.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import tree_content
from app.ai.base import ProviderError, QuotaExhausted
from app.config import settings
from app.i18n_content import digest, limits, translatable
from app.services import translation

# Бесплатный тариф Gemini ограничен по частоте: идём медленнее лимита, потому что
# упереться в 429 на середине корпуса дороже, чем подождать.
DEFAULT_DELAY = 6.0

# Пакет собирается через файлы, а не по файлу за запрос: у бесплатных тарифов
# ограничение стоит на числе запросов, а не на объёме, и урок на 3 000 знаков
# тратил на себя целый запрос из суточных двадцати. Размер подобран под лимит
# вывода модели — ответ должен поместиться целиком.
MAX_FIELDS_PER_REQUEST = 220
MAX_CHARS_PER_REQUEST = 24000


def sources(kinds: list[str], types: list[str]) -> list[tuple[str, Path]]:
    """Пары (тип документа, путь) по всем деревьям."""
    found: list[tuple[str, Path]] = []
    for kind in kinds:
        directory = settings.content_dir / tree_content.TREES[kind]["dir"]
        if "tree" in types:
            found.append(("tree", directory / "tree.json"))
        if "glossary" in types and (directory / "glossary.json").exists():
            found.append(("glossary", directory / "glossary.json"))
        for doc_type, folder in (
            ("lesson", "lessons"),
            ("scenario", "scenarios"),
            ("exercise", "exercises"),
            ("diagram", "diagrams"),
        ):
            if doc_type not in types:
                continue
            found += [(doc_type, path) for path in sorted((directory / folder).glob("*.json"))]
    return found


def batches(fields: dict[str, str]) -> list[dict[str, str]]:
    """Режет поля на пакеты по числу и по объёму."""
    out: list[dict[str, str]] = []
    current: dict[str, str] = {}
    size = 0
    for key, value in fields.items():
        if current and (
            len(current) >= MAX_FIELDS_PER_REQUEST or size + len(value) > MAX_CHARS_PER_REQUEST
        ):
            out.append(current)
            current, size = {}, 0
        current[key] = value
        size += len(value)
    if current:
        out.append(current)
    return out


def plan(pending: list[tuple[str, Path]]) -> list[list[tuple[str, Path, dict[str, str]]]]:
    """Складывает файлы в пакеты запросов.

    Один файл никогда не разрезается между запросами: перевод пишется на диск
    целиком или не пишется вовсе, иначе оборванный прогон оставит наполовину
    переведённый урок, который читается как поломка.
    """
    groups: list[list[tuple[str, Path, dict[str, str]]]] = []
    current: list[tuple[str, Path, dict[str, str]]] = []
    fields_count = size = 0

    for doc_kind, path in pending:
        document = json.loads(path.read_text(encoding="utf-8"))
        fields = translatable(doc_kind, document)
        if not fields:
            continue
        volume = sum(len(value) for value in fields.values())
        too_big = current and (
            fields_count + len(fields) > MAX_FIELDS_PER_REQUEST
            or size + volume > MAX_CHARS_PER_REQUEST
        )
        if too_big:
            groups.append(current)
            current, fields_count, size = [], 0, 0
        current.append((doc_kind, path, fields))
        fields_count += len(fields)
        size += volume
    if current:
        groups.append(current)
    return groups


def overlay_for(path: Path, language: str) -> Path:
    return tree_content.overlay_path(path, language)


def is_current(path: Path, doc_kind: str, document: dict, language: str) -> bool:
    target = overlay_for(path, language)
    if not target.exists():
        return False
    existing = json.loads(target.read_text(encoding="utf-8"))
    return existing.get("sourceDigest") == digest(doc_kind, document)


def translate_group(
    group: list[tuple[str, Path, dict[str, str]]], language: str, log, model: str | None = None
) -> list[tuple[Path, int]]:
    """Переводит пакет файлов одним запросом (или несколькими, если файл велик).

    Ключи в запросе снабжены именем файла, чтобы ответ разложился обратно без
    догадок: `d1-five-whys.json::blocks/3/text`.
    """
    combined: dict[str, str] = {}
    caps: dict[str, int] = {}
    documents: dict[str, tuple[str, Path, dict[str, Any]]] = {}
    for doc_kind, path, fields in group:
        document = json.loads(path.read_text(encoding="utf-8"))
        documents[path.name] = (doc_kind, path, document)
        for key, value in fields.items():
            combined[f"{path.name}::{key}"] = value
        for key, cap in limits(doc_kind, fields).items():
            caps[f"{path.name}::{key}"] = cap

    translated: dict[str, str] = {}
    model_id = ""
    for index, batch in enumerate(batches(combined), start=1):
        part, model_id, _ = translation.translate_fields(
            batch,
            limits={key: caps[key] for key in batch if key in caps},
            model=model,
            log=lambda message: log(f"    пакет {index}: {message}"),
        )
        translated.update(part)

    written: list[tuple[Path, int]] = []
    rejected: list[str] = []
    for name, (doc_kind, path, document) in documents.items():
        prefix = f"{name}::"
        fields = {
            key[len(prefix):]: value
            for key, value in translated.items()
            if key.startswith(prefix)
        }
        # Приёмка типизированных упражнений проверяется на собранном файле: внутри
        # общего пакета эталон и варианты живут под разными ключами.
        source_fields = translatable(doc_kind, document)
        problems = translation.validate(
            source_fields,
            fields,
            document if doc_kind == "exercise" else None,
            limits(doc_kind, source_fields),
        )
        if problems:
            # Один спорный абзац не отменяет остальных девяти файлов пакета: они
            # проверены и переведены верно. Виновный останется непереведённым и
            # попадёт в следующий прогон.
            rejected.append(f"{name} ({problems[0]})")
            continue
        written.append(
            (write_overlay(doc_kind, path, document, fields, language, model_id), len(fields))
        )
    return written, rejected


def write_overlay(
    doc_kind: str,
    path: Path,
    document: dict[str, Any],
    fields: dict[str, str],
    language: str,
    model_id: str,
) -> Path:
    target = overlay_for(path, language)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "language": language,
        "sourceDigest": digest(doc_kind, document),
        # Машинный перевод помечен явно: вычитанный человеком файл ставит
        # "reviewed" руками, и по репозиторию видно, что уже проверено.
        "translationStatus": "machine",
        "generator": {
            "provider": "gemini",
            "model": model_id,
            "promptVersion": translation.PROMPT_VERSION,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "fields": fields,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="en", help="язык перевода")
    parser.add_argument("--kind", choices=[*tree_content.KINDS, "all"], default="all")
    parser.add_argument(
        "--type",
        action="append",
        choices=["tree", "lesson", "scenario", "exercise", "glossary", "diagram"],
        help="только документы этого типа; можно повторять",
    )
    parser.add_argument("--only", action="append", help="имя файла без .json; можно повторять")
    parser.add_argument("--limit", type=int, help="остановиться после N файлов")
    parser.add_argument("--force", action="store_true", help="переписать даже актуальные")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument(
        "--model",
        default=None,
        help="модели через запятую; квота бесплатного тарифа считается на модель, "
        "поэтому исчерпав одну, прогон переходит к следующей",
    )
    parser.add_argument("--dry-run", action="store_true", help="только показать, что делать")
    args = parser.parse_args()

    kinds = list(tree_content.KINDS) if args.kind == "all" else [args.kind]
    types = args.type or ["tree", "lesson", "scenario", "exercise", "glossary", "diagram"]

    todo = []
    skipped = 0
    for doc_kind, path in sources(kinds, types):
        if args.only and path.stem not in args.only:
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if not args.force and is_current(path, doc_kind, document, args.language):
            skipped += 1
            continue
        todo.append((doc_kind, path))

    if args.limit:
        todo = todo[: args.limit]

    groups = plan(todo)
    print(
        f"к переводу: {len(todo)} файлов в {len(groups)} запросах, "
        f"уже актуально: {skipped}"
    )
    if args.dry_run:
        for group in groups[:10]:
            volume = sum(sum(len(v) for v in fields.values()) for _, _, fields in group)
            names = ", ".join(path.stem for _, path, _ in group)
            print(f"  {volume:6} знаков: {names[:110]}")
        return 0

    models = (
        [name.strip() for name in args.model.split(",") if name.strip()]
        if args.model
        else list(settings.translation_models)
    )
    current = 0
    print(f"модели: {', '.join(models)}")

    done = failed = 0
    for index, group in enumerate(groups, start=1):
        names = ", ".join(path.stem for _, path, _ in group)
        prefix = f"[{index}/{len(groups)}]"
        while True:
            try:
                written, rejected = translate_group(
                    group,
                    args.language,
                    lambda message: print(message, flush=True),
                    models[current],
                )
                done += len(written)
                failed += len(rejected)
                fields_total = sum(count for _, count in written)
                print(
                    f"{prefix} {len(written)} файлов, {fields_total} полей: {names[:80]}",
                    flush=True,
                )
                for name in rejected:
                    print(f"{prefix} НЕ переведён — {name}", file=sys.stderr, flush=True)
                break
            except QuotaExhausted as error:
                # Квота считается на модель: следующая в цепочке ещё не тронута.
                # Тот же пакет переводится ею заново — потерянного нет.
                current += 1
                if current >= len(models):
                    print(f"\n{prefix} остановлено: {error}", file=sys.stderr, flush=True)
                    print(
                        f"все модели исчерпаны. Переведено за прогон: {done} файлов. "
                        "Повторите запуск после сброса квоты — актуальные файлы "
                        "будут пропущены.",
                        file=sys.stderr,
                    )
                    return 2
                print(
                    f"{prefix} квота модели {models[current - 1]} исчерпана, "
                    f"перехожу на {models[current]}",
                    flush=True,
                )
            except ProviderError as error:
                failed += len(group)
                print(f"{prefix} НЕ переведён — {error}", file=sys.stderr, flush=True)
                break
            except Exception as error:  # noqa: BLE001 — прогон не должен падать на пакете
                failed += len(group)
                print(f"{prefix} ошибка — {error}", file=sys.stderr, flush=True)
                break
        if index < len(groups):
            time.sleep(args.delay)

    print(f"\nпереведено: {done}, не вышло: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
