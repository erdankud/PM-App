"""Перевод контента: что переводится, что нет, и как перевод ложится на исходник.

Авторский корпус написан по-русски и остаётся единственным источником структуры.
Перевод хранится **отдельным наложением** — `content/i18n/<язык>/<то же имя>.json` —
и приезжает поверх исходника при чтении. Два следствия, ради которых так и сделано:

1. Прогон переводчика физически не может испортить авторский текст: он пишет в другой
   каталог. 1,7 млн символов не восстанавливаются из ошибки в скрипте.
2. Рубрика гейта, веса вариантов и QA-фикстуры существуют в одном экземпляре и
   переводу не подлежат. «Язык не меняет оценку» становится свойством конструкции,
   а не дисциплины: переводить нечего, потому что переводимых путей там нет.

`sourceDigest` в наложении — отпечаток переводимой части исходника. Правка урока
делает перевод несовременным, и он перестаёт применяться: показать прошлую редакцию
на другом языке хуже, чем показать текущую на языке оригинала.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from typing import Any, Iterator

AUTHORED_LANGUAGE = "ru"

# Языки, для которых бывают наложения. Русский — сам исходник.
TRANSLATED_LANGUAGES = ("en",)

CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")


# --- Что переводится ---------------------------------------------------------
#
# Список путей задан явно, а не выведен из схемы, потому что это граница
# корректности: лишний путь здесь означает, что модель перепишет то, от чего
# зависит балл.

#: Поля блока контента (`blocks`, `promptBlocks`, `referenceReasoningBlocks`).
#: `diagramId`, `type`, `tone`, `ordered` — структура, не текст.
_BLOCK_TEXT_FIELDS = ("text", "title", "subtitle")

SPECS: dict[str, dict[str, Any]] = {
    "lesson": {
        "fields": ("title", "keyTakeaway", "checkQuestion"),
        "blocks": ("blocks",),
        "sectioned": ("sections",),
    },
    "scenario": {
        "fields": ("title", "summary", "decisionPrompt"),
        "objects": {
            "brief": ("role", "company", "context", "objective", "constraints", "task"),
            "learnTakeaway": ("title", "body"),
        },
        "lists": {
            "evidenceCards": ("title", "content"),
            "decisionOptions": ("label", "description", "consequence"),
            # `gap` — единственное переводимое поле внутри рубрики: его видит человек,
            # когда гейт не сдан. Всё остальное в рубрике кормит оценщика и остаётся
            # в одном экземпляре.
            "rubric.remediation": ("gap",),
        },
    },
    "exercise": {
        "fields": ("title",),
        "blocks": ("promptBlocks", "referenceReasoningBlocks"),
        "lists": {
            "inputs": ("label", "unit"),
            # `expected` — эталон, с которым сверяется ответ. Он обязан переводиться
            # вместе с `choices`, иначе выбранный вариант перестанет совпадать с
            # эталоном и упражнение начнёт врать (`tests/test_system_design.py`
            # отправляет эталоны обратно и требует совпадения).
            "acceptance": ("expected",),
        },
        "list_of_strings": {"inputs": ("choices",)},
    },
    "glossary": {
        # `termEn` уже написан автором — английский термин не выдумывается заново,
        # он и есть перевод `term`. У пяти терминов автор поставил прочерк: там
        # эквивалента нет, и русское название переводится наравне с определением
        # (см. `_glossary_extras`).
        "lists": {"terms": ("definition",)},
        "glossary": True,
    },
    "diagram": {
        "fields": ("title",),
        "lists": {"nodes": ("label",), "edges": ("label",)},
    },
    "tree": {
        "fields": ("sourceAttribution",),
        # Названия колец — продуктовая копия, а не машинный вывод: они лежат в
        # `titleEn` / `subtitleEn` рядом с русскими, как `titleEn` у домена.
        "nested": True,
    },
}


# --- Ограничения длины -------------------------------------------------------
#
# Берутся из тех же JSON-схем, что проверяют авторский контент: держать второй
# список пределов в переводчике значит однажды разойтись со схемой. Английский
# бывает длиннее русского, и без этой проверки перевод молча ломает валидацию
# контента — а увидеть это можно только на следующем прогоне.

_SCHEMA_FILES = {
    "lesson": "lesson.schema.json",
    "scenario": "gate-scenario.schema.json",
    "exercise": "exercise.schema.json",
    "glossary": "glossary.schema.json",
    "diagram": "diagram.schema.json",
    "tree": "tree.schema.json",
}


@lru_cache
def _schema(kind: str) -> dict[str, Any]:
    from app.config import settings

    return json.loads((settings.content_dir / _SCHEMA_FILES[kind]).read_text(encoding="utf-8"))


def _resolve(node: Any, root: dict[str, Any]) -> Any:
    """Разыменовывает локальный `$ref`; чужие ссылки схемы не используют."""
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 8:
        target = node["$ref"].lstrip("#/").split("/")
        node = root
        for part in target:
            node = (node or {}).get(part)
        seen += 1
    return node


def max_length(kind: str, path: str) -> int | None:
    """Предел длины поля по схеме, если он там задан."""
    if kind not in _SCHEMA_FILES:
        return None
    root = _schema(kind)
    node: Any = root
    for part in path.split("/"):
        node = _resolve(node, root)
        if not isinstance(node, dict):
            return None
        if part.isdigit():
            node = node.get("items")
        else:
            node = (node.get("properties") or {}).get(part)
    node = _resolve(node, root)
    return node.get("maxLength") if isinstance(node, dict) else None


def limits(kind: str, fields: dict[str, str]) -> dict[str, int]:
    """Пределы для набора переводимых путей — только там, где они есть."""
    found = {}
    for path in fields:
        cap = max_length(kind, path)
        if cap:
            found[path] = cap
    return found


def _walk_block(block: dict[str, Any], prefix: str) -> Iterator[tuple[str, str]]:
    for field in _BLOCK_TEXT_FIELDS:
        if isinstance(block.get(field), str) and block[field]:
            yield f"{prefix}/{field}", block[field]
    for index, item in enumerate(block.get("items") or []):
        if isinstance(item, str) and item:
            yield f"{prefix}/items/{index}", item
    for index, cell in enumerate(block.get("header") or []):
        if isinstance(cell, str) and cell:
            yield f"{prefix}/header/{index}", cell
    for row_index, row in enumerate(block.get("rows") or []):
        for cell_index, cell in enumerate(row or []):
            if isinstance(cell, str) and cell:
                yield f"{prefix}/rows/{row_index}/{cell_index}", cell


def _walk_list(document: dict[str, Any], path: str, fields: tuple[str, ...]) -> Iterator[tuple[str, str]]:
    node: Any = document
    for part in path.split("."):
        if not isinstance(node, dict):
            return
        node = node.get(part)
    if not isinstance(node, list):
        return
    prefix = path.replace(".", "/")
    for index, item in enumerate(node):
        if not isinstance(item, dict):
            continue
        for field in fields:
            if isinstance(item.get(field), str) and item[field]:
                yield f"{prefix}/{index}/{field}", item[field]


def translatable(kind: str, document: dict[str, Any]) -> dict[str, str]:
    """Плоская карта «путь → русский текст» для одного документа."""
    spec = SPECS[kind]
    out: dict[str, str] = {}

    for field in spec.get("fields", ()):
        value = document.get(field)
        if isinstance(value, str) and value:
            out[field] = value

    for name, fields in (spec.get("objects") or {}).items():
        node = document.get(name)
        if isinstance(node, dict):
            for field in fields:
                if isinstance(node.get(field), str) and node[field]:
                    out[f"{name}/{field}"] = node[field]

    for path, fields in (spec.get("lists") or {}).items():
        out.update(dict(_walk_list(document, path, fields)))

    for name, fields in (spec.get("list_of_strings") or {}).items():
        for index, item in enumerate(document.get(name) or []):
            if not isinstance(item, dict):
                continue
            for field in fields:
                for choice_index, choice in enumerate(item.get(field) or []):
                    if isinstance(choice, str) and choice:
                        out[f"{name}/{index}/{field}/{choice_index}"] = choice

    for name in spec.get("blocks", ()):
        for index, block in enumerate(document.get(name) or []):
            if isinstance(block, dict):
                out.update(dict(_walk_block(block, f"{name}/{index}")))

    for name in spec.get("sectioned", ()):
        for section_index, section in enumerate(document.get(name) or []):
            for index, block in enumerate((section or {}).get("blocks") or []):
                if isinstance(block, dict):
                    out.update(
                        dict(_walk_block(block, f"{name}/{section_index}/blocks/{index}"))
                    )

    if spec.get("nested"):
        out.update(_tree_extras(document))
    if spec.get("glossary"):
        out.update(_glossary_extras(document))
    return out


def has_authored_english(value: str | None) -> bool:
    """Прочерк в `termEn` — это «эквивалента нет», а не английское слово."""
    return bool(value) and value.strip() not in {"—", "-", "–"}


def _glossary_extras(glossary: dict[str, Any]) -> dict[str, str]:
    return {
        f"terms/{index}/term": term["term"]
        for index, term in enumerate(glossary.get("terms") or [])
        if term.get("term") and not has_authored_english(term.get("termEn"))
    }


def _tree_extras(tree: dict[str, Any]) -> dict[str, str]:
    """Карта: названия доменов, блоков и узлов.

    `titleEn` у домена уже написан автором, `models` — имена моделей («5 Whys»,
    «HEART»), которые остаются как есть на любом языке.
    """
    out: dict[str, str] = {}
    for index, domain in enumerate(tree.get("domains") or []):
        if domain.get("keyQuestion"):
            out[f"domains/{index}/keyQuestion"] = domain["keyQuestion"]
    for block_index, block in enumerate(tree.get("blocks") or []):
        if block.get("title"):
            out[f"blocks/{block_index}/title"] = block["title"]
        for node_index, node in enumerate(block.get("nodes") or []):
            for field in ("title", "keyQuestion", "pmDecision"):
                if isinstance(node.get(field), str) and node[field]:
                    out[f"blocks/{block_index}/nodes/{node_index}/{field}"] = node[field]
    return out


# --- Наложение ---------------------------------------------------------------


def digest(kind: str, document: dict[str, Any]) -> str:
    """Отпечаток переводимой части. Меняется только вместе с текстом, который
    надо переводить заново, — правка веса варианта перевод не обесценивает."""
    payload = json.dumps(translatable(kind, document), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _assign(document: dict[str, Any], path: str, value: str) -> bool:
    node: Any = document
    parts = path.split("/")
    for part in parts[:-1]:
        key: Any = int(part) if part.isdigit() else part
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return False
    last: Any = int(parts[-1]) if parts[-1].isdigit() else parts[-1]
    try:
        node[last] = value
    except (KeyError, IndexError, TypeError):
        return False
    return True


#: Поля, английский вариант которых автор уже написал. Их не переводят заново:
#: «Discovery & Research» и «Response cache» существуют в исходнике, и машинный
#: перевод русского названия дал бы второй, расходящийся с ним вариант.
AUTHORED_EN = {
    "tree": (
        ("domains", "titleEn", "title"),
        ("tiers", "titleEn", "title"),
        ("tiers", "subtitleEn", "subtitle"),
    ),
    "glossary": (("terms", "termEn", "term"),),
}


def _use_authored_english(kind: str, document: dict[str, Any]) -> None:
    for collection, source_field, target_field in AUTHORED_EN.get(kind, ()):
        for item in document.get(collection) or []:
            if isinstance(item, dict) and has_authored_english(item.get(source_field)):
                item[target_field] = item[source_field]


def apply_overlay(
    kind: str,
    document: dict[str, Any],
    overlay: dict[str, Any] | None,
    language: str = "en",
) -> dict[str, Any]:
    """Кладёт перевод на копию документа.

    Несовременное наложение (исходник правили после перевода) игнорируется целиком:
    смешивать свежий русский с переводом прошлой редакции — это показать человеку
    текст, которого в уроке уже нет.
    """
    current = overlay and overlay.get("sourceDigest") == digest(kind, document)
    if not current and language != "en":
        return document

    merged = json.loads(json.dumps(document))
    if current:
        for path, value in (overlay.get("fields") or {}).items():
            if isinstance(value, str) and value:
                _assign(merged, path, value)
    if language == "en":
        # После наложения, а не до: авторский английский главнее машинного. Работает
        # и без перевода — названия доменов и термины уже английские в исходнике,
        # и показывать их по-русски незачем ни минуты.
        _use_authored_english(kind, merged)
    return merged
