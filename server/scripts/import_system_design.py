#!/usr/bin/env python3
"""Импорт домена System Design из авторского markdown в контент-файлы.

    python -m scripts.import_system_design ~/Downloads/files/system-design-course.md

Курс написан целиком в одном markdown с жёстким форматом (см. его раздел
«Формат урока» и «Нотация схем»), поэтому источник разбирается, а не
переписывается руками: 18 блоков, 96 узлов, 158 уроков, 96 упражнений,
36 сценариев и глоссарии по блокам.

Сценарии гейтов кладутся в `scenarios-draft/`: в источнике нет ни весов опций, ни
QA-фикстур, без которых сценарий по схеме публиковать нельзя. Дописанный сценарий
переезжает в `scenarios/`, и его блок можно публиковать.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "system-design"

AREAS = [
    ("data", "Данные и хранение", "Data & Storage", "DS",
     "Где живут данные продукта и что мешает их изменить?"),
    ("integration", "Взаимодействие компонентов", "Component Interaction", "IN",
     "Как части системы договариваются и почему ломаются?"),
    ("scale", "Масштаб и надёжность", "Scale & Reliability", "SC",
     "Что произойдёт, когда пользователей станет в 100 раз больше?"),
    ("performance", "Производительность и стоимость", "Performance & Cost", "PF",
     "Сколько стоит секунда ожидания и сколько — один запрос?"),
    ("ai_systems", "AI-системы", "AI Systems", "AI",
     "Из чего состоит AI-фича и почему она дорожает быстрее, чем растёт?"),
    ("security", "Безопасность и приватность", "Security & Privacy", "SE",
     "Кто что видит и что мы обязаны уметь удалить?"),
]
TIERS = {
    1: ("Читатель системы", "Понять, что происходит"),
    2: ("Участник решения", "Оценить компромисс"),
    3: ("Автор требований", "Задать рамку"),
}
SECTION_KINDS = [
    ("Вопрос", "question"),
    ("Цена", "cost"),
    ("Суть", "substance"),
    ("На «Полке»", "example"),
    ("Границы", "limits"),
    ("Вывод", "takeaway"),
]
SECTION_BY_TITLE = dict(SECTION_KINDS)

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    out = []
    for ch in text:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    result = re.sub(r"-+", "-", "".join(out)).strip("-")
    return result or "term"


def norm_term(text: str) -> str:
    """Ключ для сопоставления [[термин]] с глоссарием: регистр и окончание не важны."""
    return re.sub(r"[^a-zа-я0-9]+", "", text.lower().replace("ё", "е"))


# --- разбор markdown ---------------------------------------------------------


def split_sections(lines: list[str], level: int) -> list[tuple[str, list[str]]]:
    """Куски документа по заголовкам заданного уровня."""
    marker = "#" * level + " "
    chunks: list[tuple[str, list[str]]] = []
    title: str | None = None
    body: list[str] = []
    for line in lines:
        if line.startswith(marker) and not line.startswith(marker + "#"):
            if title is not None:
                chunks.append((title, body))
            title, body = line[len(marker):].strip(), []
        elif title is not None:
            body.append(line)
    if title is not None:
        chunks.append((title, body))
    return chunks


def parse_table(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def plain_text(text: str) -> str:
    """Текст без разметки терминов — для подсчёта длины и поиска."""
    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        return inner.split("|", 1)[1] if "|" in inner else inner

    return re.sub(r"\[\[([^\]]+)\]\]", repl, text)


def link_terms(text: str, by_norm: dict[str, str]) -> str:
    """Переписывает `[[термин]]` в `[[id|как в тексте]]`.

    Клиент подчёркивает такие места пунктиром и открывает карточку по тапу, поэтому
    разметка должна дожить до него — но уже с идентификатором, чтобы клиенту не
    приходилось гадать, какое слово какому термину соответствует. Неизвестный термин
    разворачивается в обычный текст: подчёркивание, которое никуда не ведёт, хуже
    его отсутствия.
    """
    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        lookup, shown = (inner.split("|", 1) if "|" in inner else (inner, inner))
        term_id = by_norm.get(norm_term(lookup))
        return f"[[{term_id}|{shown}]]" if term_id else shown

    return re.sub(r"\[\[([^\]]+)\]\]", repl, text)


def blocks_from(lines: list[str], diagrams: dict[str, dict]) -> list[dict[str, Any]]:
    """Абзацы, списки, таблицы, схемы и код внутри секции урока."""
    blocks: list[dict[str, Any]] = []
    buffer: list[str] = []
    index = 0

    def flush() -> None:
        if not buffer:
            return
        text = " ".join(s.strip() for s in buffer).strip()
        buffer.clear()
        if text:
            blocks.append({"type": "paragraph", "text": text})

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped == "---":
            flush()
            index += 1
            continue

        if stripped.startswith("```"):
            fence = stripped[3:].strip()
            body: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                body.append(lines[index])
                index += 1
            index += 1
            flush()
            if fence == "yaml" and any(s.startswith("nodes:") for s in body):
                diagram = parse_diagram(body)
                if diagram:
                    diagrams[diagram["id"]] = diagram
                    blocks.append({"type": "diagram_ref", "diagramId": diagram["id"]})
            else:
                blocks.append({"type": "code", "text": "\n".join(body)})
            continue

        if not stripped:
            flush()
        elif stripped.startswith("|"):
            flush()
            table: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table.append(lines[index])
                index += 1
            rows = parse_table(table)
            if rows:
                blocks.append({"type": "table", "header": rows[0], "rows": rows[1:]})
            continue
        elif re.match(r"^([-*]|\d+\.)\s+", stripped):
            flush()
            items: list[str] = []
            while index < len(lines) and re.match(r"^([-*]|\d+\.)\s+", lines[index].strip()):
                items.append(re.sub(r"^([-*]|\d+\.)\s+", "", lines[index].strip()))
                index += 1
            if len(items) == 1:
                # Список из одного пункта — это абзац, а не список.
                blocks.append({"type": "paragraph", "text": items[0]})
            else:
                block: dict[str, Any] = {"type": "list", "items": items}
                if re.match(r"^\d+\.", stripped):
                    block["ordered"] = True
                blocks.append(block)
            continue
        else:
            buffer.append(line)
        index += 1

    flush()
    return blocks


def parse_diagram(body: list[str]) -> dict[str, Any] | None:
    """Схема в нотации курса: id/title/nodes/edges."""
    text = "\n".join(body)
    ident = re.search(r"^id:\s*(\S+)", text, re.M)
    if not ident:
        return None
    title = re.search(r"^title:\s*(.+)$", text, re.M)
    nodes, edges = [], []
    for match in re.finditer(r"^\s*-\s*\{([^}]*)\}", text, re.M):
        fields = {}
        for pair in match.group(1).split(","):
            if ":" not in pair:
                continue
            key, value = pair.split(":", 1)
            fields[key.strip()] = value.strip().strip('"').strip("'")
        if "type" in fields and "from" not in fields:
            nodes.append({"id": fields["id"], "type": fields["type"], "label": fields.get("label", "")})
        elif "from" in fields:
            edge = {"from": fields["from"], "to": fields["to"], "type": fields.get("type", "sync")}
            if fields.get("label"):
                edge["label"] = fields["label"]
            edges.append(edge)
    return {
        "id": ident.group(1),
        "title": title.group(1).strip() if title else "",
        "nodes": nodes,
        "edges": edges,
    }


# --- сборка контента ---------------------------------------------------------


def _link_block(block: dict[str, Any], by_norm: dict[str, str]) -> dict[str, Any]:
    """Проставляет ссылки на термины во всех текстовых полях блока."""
    linked = dict(block)
    if "text" in linked:
        linked["text"] = link_terms(linked["text"], by_norm)
    if "items" in linked:
        linked["items"] = [link_terms(item, by_norm) for item in linked["items"]]
    if "rows" in linked:
        linked["rows"] = [[link_terms(cell, by_norm) for cell in row] for row in linked["rows"]]
    return linked


def area_for(prefix: str) -> tuple[str, str, str]:
    for key, title, _title_en, code, question in AREAS:
        if code == prefix:
            return key, title, question
    raise SystemExit(f"неизвестная область: {prefix}")


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if source is None or not source.exists():
        print("укажите путь к system-design-course.md")
        return 2
    lines = source.read_text(encoding="utf-8").splitlines()
    top = split_sections(lines, 2)

    glossary: dict[str, dict[str, Any]] = {}
    by_norm: dict[str, str] = {}
    blocks: dict[str, dict[str, Any]] = {}
    lessons: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    scenarios: list[dict[str, Any]] = []
    diagrams: dict[str, dict[str, Any]] = {}
    opens: dict[str, list[str]] = {}

    # 1. глоссарии
    for title, body in top:
        match = re.match(r"^Глоссарий\s+([A-Z]{2}\d)$", title)
        if not match:
            continue
        block_id = match.group(1)
        for row in parse_table(body)[1:]:
            if len(row) < 3:
                continue
            term, term_en, definition = row[0], row[1], row[2]
            base = slug(term_en.split(",")[0]) or slug(term)
            term_id = base
            suffix = 2
            while term_id in glossary and glossary[term_id]["term"] != term:
                term_id = f"{base}-{suffix}"
                suffix += 1
            glossary.setdefault(term_id, {
                "id": term_id,
                "term": term,
                "termEn": term_en,
                "definition": definition,
                "blockId": block_id,
                "sourceLessonId": None,
                "relatedIds": [],
            })
            by_norm.setdefault(norm_term(term), term_id)

    # 2. блоки, узлы, уроки
    for title, body in top:
        match = re.match(r"^Блок\s+([A-Z]{2})(\d)\s+—\s+(.+)$", title)
        if not match:
            continue
        prefix, tier_s, block_title = match.group(1), match.group(2), match.group(3).strip()
        block_id = f"{prefix}{tier_s}"
        tier = int(tier_s)
        area_key, area_title, _ = area_for(prefix)
        header = "\n".join(body[:12])
        unlocks = re.search(r"^\*\*Открывает:\*\*\s*(.+)$", header, re.M)
        opens[block_id] = (
            [x.strip("` ").upper() for x in unlocks.group(1).split(",")] if unlocks else []
        )

        nodes: list[dict[str, Any]] = []
        for node_index, (node_title, node_body) in enumerate(split_sections(body, 3), start=1):
            node_match = re.match(r"^Узел\s+([A-Z]{2}\d-N\d+)\s+·\s+(.+)$", node_title)
            if not node_match:
                continue
            node_id = node_match.group(1).lower()
            head = "\n".join(node_body[:8])
            key_question = re.search(r"^\*\*Ключевой вопрос:\*\*\s*(.+)$", head, re.M)
            pm_decision = re.search(r"^\*\*`pm_decision`:\*\*\s*(.+)$", head, re.M)
            nodes.append({
                "id": node_id,
                "title": node_match.group(2).strip(),
                "keyQuestion": (key_question.group(1).strip() if key_question else ""),
                "pmDecision": (pm_decision.group(1).strip() if pm_decision else ""),
                "models": [],
                "aiImpact": None,
                "order": node_index,
            })

            for lesson_index, (lesson_title, lesson_body) in enumerate(
                split_sections(node_body, 4), start=1
            ):
                lesson_match = re.match(r"^Урок\s+([A-Z]{2}\d-N\d+-L\d+)\s+·\s+(.+)$", lesson_title)
                if not lesson_match:
                    continue
                lesson_id = lesson_match.group(1).lower()
                sections: list[dict[str, Any]] = []
                current: str | None = None
                buffer: list[str] = []
                for line in lesson_body:
                    heading = re.match(r"^\*\*(.+?)\*\*$", line.strip())
                    if heading and heading.group(1) in SECTION_BY_TITLE:
                        if current:
                            sections.append((current, buffer))  # type: ignore[arg-type]
                        current, buffer = SECTION_BY_TITLE[heading.group(1)], []
                    elif current is not None:
                        buffer.append(line)
                if current:
                    sections.append((current, buffer))  # type: ignore[arg-type]

                built: list[dict[str, Any]] = []
                raw_text: list[str] = []
                for kind, section_lines in sections:  # type: ignore[misc]
                    raw_text.extend(section_lines)
                    built.append({
                        "kind": kind,
                        "blocks": [
                            _link_block(b, by_norm)
                            for b in blocks_from(section_lines, diagrams)
                        ],
                    })
                joined = "\n".join(raw_text)
                term_ids: list[str] = []
                for raw in re.findall(r"\[\[([^\]]+)\]\]", joined):
                    key = norm_term(raw.split("|", 1)[0])
                    term_id = by_norm.get(key)
                    if term_id and term_id not in term_ids:
                        term_ids.append(term_id)
                        if glossary[term_id]["sourceLessonId"] is None:
                            glossary[term_id]["sourceLessonId"] = lesson_id
                takeaway = next(
                    (
                        b["text"]
                        for s in built if s["kind"] == "takeaway"
                        for b in s["blocks"] if b.get("type") == "paragraph"
                    ),
                    "",
                )
                words = len(re.findall(r"\w+", plain_text(joined)))
                lessons.append({
                    "id": lesson_id,
                    "nodeId": node_id,
                    "blockId": block_id,
                    "order": lesson_index,
                    "version": 1,
                    "title": lesson_match.group(2).strip(),
                    # В источнике времени нет. Спека (§2.1) задаёт для System Design
                    # 12–15 минут; раскладываем полосу по длине урока.
                    "estimatedMinutes": 12 + max(0, min(3, round((words - 250) / 100))),
                    "keyTakeaway": takeaway,
                    "sections": built,
                    "termIds": term_ids,
                    "diagramIds": [
                        b["diagramId"] for s in built for b in s["blocks"]
                        if b.get("type") == "diagram_ref"
                    ],
                    "exerciseId": None,
                    "crossRefs": [],
                })

        blocks[block_id] = {
            "id": block_id,
            "domainKey": area_key,
            "tier": tier,
            "title": block_title,
            "prerequisiteBlockIds": [],
            "status": "coming_soon",
            "nodes": nodes,
        }
        blocks[block_id]["_area_title"] = area_title

    # 3. упражнения
    for title, body in top:
        match = re.match(r"^Упражнения\s+([A-Z]{2}\d)$", title)
        if not match:
            continue
        block_id = match.group(1)
        text = "\n".join(body)
        pattern = re.compile(
            r"^\*\*(EX-[A-Z0-9-]+)\s+·\s+(.+?)\*\*\s*\*\(к\s+([A-Z0-9-]+)\)\*\s*$", re.M
        )
        matches = list(pattern.finditer(text))
        for position, found in enumerate(matches):
            start = found.end()
            end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
            chunk = text[start:end].strip().split("\n")
            prompt_lines, reference_lines, in_reference = [], [], False
            for line in chunk:
                marker = next(
                    (m for m in ("*Эталон:*", "*Эталон-ориентир:*")
                     if line.strip().startswith(m)),
                    None,
                )
                if marker:
                    in_reference = True
                    reference_lines.append(line.strip()[len(marker):].strip())
                elif in_reference:
                    reference_lines.append(line)
                elif line.strip() != "---":
                    prompt_lines.append(line)
            exercises.append({
                "id": found.group(1).lower(),
                "nodeId": found.group(3).lower(),
                "blockId": block_id,
                "type": "open",
                "title": found.group(2).strip(),
                "promptBlocks": blocks_from(prompt_lines, diagrams),
                "inputs": [],
                "acceptance": [],
                "referenceReasoningBlocks": blocks_from(reference_lines, diagrams),
                "estimatedMinutes": 8,
            })

    # 4. сценарии гейтов — как черновики: в источнике нет ни весов опций, ни фикстур
    for title, body in top:
        match = re.match(r"^Гейт\s+([A-Z]{2}\d)$", title)
        if not match:
            continue
        block_id = match.group(1)
        for scenario_title, scenario_body in split_sections(body, 3):
            scenario_match = re.match(r"^Сценарий\s+([A-Z0-9-]+)\s+·\s+(.+)$", scenario_title)
            if not scenario_match:
                continue
            text = "\n".join(scenario_body)
            covered = re.search(r"covered_lesson_ids:\s*\[([^\]]+)\]", text)
            covered_ids = (
                [x.strip().lower() for x in covered.group(1).split(",")] if covered else []
            )
            brief = re.search(r"\*\*Бриф\*\*\n(.*?)(?=\n\*\*Evidence\*\*)", text, re.S)
            evidence = re.search(r"\*\*Evidence\*\*\n(.*?)(?=\n\*\*Решение)", text, re.S)
            prompt = re.search(r"\*\*Решение:\*\*\s*(.+)", text)
            options: list[dict[str, Any]] = []
            # Описание опции живёт на той же строке, что и её название: если
            # позволить разделителю съесть перенос, опция без описания поглотит
            # следующую целиком.
            for opt in re.finditer(
                r"^\*\*([A-D])\.\s+(.+?)\*\*[ \t]*([^\n]*)\n\*Последствия:\*\s*(.*?)(?=\n\n|\n\*\*[A-D]\.|\Z)",
                text, re.S | re.M,
            ):
                options.append({
                    "id": opt.group(1),
                    "label": opt.group(2).strip().rstrip("."),
                    "description": " ".join(opt.group(3).split()),
                    "consequence": " ".join(opt.group(4).split()),
                })
            positives = []
            positive_block = re.search(
                r"\*Positive signals\*\n\n(.*?)(?=\n\*Defensible|\n\*Negative)", text, re.S
            )
            if positive_block:
                for row in parse_table(positive_block.group(1).splitlines())[1:]:
                    if len(row) >= 2:
                        lesson = row[1].strip("` ")
                        positives.append({
                            "signal": plain_text(row[0]),
                            "lessonId": lesson.lower() if lesson != "—" else None,
                        })
            negatives = []
            negative_block = re.search(
                r"\*Negative signals\*\n\n(.*?)(?=\n\*Remediation|\Z)", text, re.S
            )
            if negative_block:
                negatives = [
                    plain_text(line.strip()[2:])
                    for line in negative_block.group(1).splitlines()
                    if line.strip().startswith("- ")
                ]
            remediation = []
            remediation_block = re.search(r"\*Remediation\*\n\n(.*?)\Z", text, re.S)
            if remediation_block:
                for row in parse_table(remediation_block.group(1).splitlines())[1:]:
                    if len(row) >= 2:
                        for lesson in row[1].split(","):
                            lesson = lesson.strip("` ")
                            if lesson and lesson != "—":
                                remediation.append({"gap": row[0], "lessonId": lesson.lower()})
            reference = re.search(r"\*Reference:\*\s*(.+)", text)
            # Сырой разбор защитимых альтернатив: из него выводятся веса опций,
            # которых в источнике нет числами.
            defensible = re.search(
                r"\*Defensible alternatives\*\n(.*?)(?=\n\*Negative)", text, re.S
            )
            scenarios.append({
                "id": scenario_match.group(1).lower(),
                "version": 1,
                "status": "draft",
                "blockId": block_id,
                "coveredLessonIds": covered_ids,
                "title": scenario_match.group(2).strip(),
                "brief": " ".join(brief.group(1).split()) if brief else "",
                "evidenceRaw": evidence.group(1).strip() if evidence else "",
                "decisionPrompt": prompt.group(1).strip() if prompt else "",
                "options": options,
                "rubric": {
                    "reference": reference.group(1).strip() if reference else "",
                    "defensible": defensible.group(1).strip() if defensible else "",
                    "positiveSignals": positives,
                    "negativeSignals": negatives,
                    "remediation": remediation,
                },
            })

    # 5. граф разблокировки из «Открывает» в шапках блоков
    for block_id, targets in opens.items():
        for target in targets:
            if target in blocks and block_id not in blocks[target]["prerequisiteBlockIds"]:
                blocks[target]["prerequisiteBlockIds"].append(block_id)

    order = [f"{code}{tier}" for *_, code, _ in AREAS for tier in (1, 2, 3)]
    tree = {
        "version": 1,
        "kind": "system_design",
        "sourceAttribution": "System Design для PM — оригинальный контент курса.",
        "domains": [
            {"key": key, "title": title, "titleEn": title_en,
             "order": index, "keyQuestion": question}
            for index, (key, title, title_en, _code, question) in enumerate(AREAS, start=1)
        ],
        "tiers": [
            {"tier": tier, "title": TIERS[tier][0], "subtitle": TIERS[tier][1]}
            for tier in (1, 2, 3)
        ],
        "blocks": [
            {k: v for k, v in blocks[b].items() if not k.startswith("_")}
            for b in order if b in blocks
        ],
    }

    # Публикация блока — редакторское решение, а не данные источника: у уже
    # существующего дерева статусы переносятся, иначе повторный импорт снимет
    # с публикации всё, что было опубликовано.
    existing = OUT / "tree.json"
    if existing.exists():
        previous = {
            block["id"]: block["status"]
            for block in json.loads(existing.read_text(encoding="utf-8"))["blocks"]
        }
        for block in tree["blocks"]:
            block["status"] = previous.get(block["id"], block["status"])

    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("lessons", "exercises", "scenarios-draft", "diagrams"):
        (OUT / name).mkdir(exist_ok=True)

    def dump(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    dump(OUT / "tree.json", tree)
    dump(OUT / "glossary.json", {"version": 1, "terms": list(glossary.values())})
    for lesson in lessons:
        dump(OUT / "lessons" / f"{lesson['id']}.json", lesson)
    for exercise in exercises:
        dump(OUT / "exercises" / f"{exercise['id']}.json", exercise)
    for scenario in scenarios:
        dump(OUT / "scenarios-draft" / f"{scenario['id']}.json", scenario)
    for diagram in diagrams.values():
        dump(OUT / "diagrams" / f"{diagram['id']}.json", diagram)

    unresolved = sum(1 for t in glossary.values() if t["sourceLessonId"] is None)
    print(f"блоков: {len(tree['blocks'])}  узлов: {sum(len(b['nodes']) for b in tree['blocks'])}")
    print(f"уроков: {len(lessons)}  упражнений: {len(exercises)}  сценариев: {len(scenarios)}")
    print(f"терминов: {len(glossary)} (без урока-источника: {unresolved})  схем: {len(diagrams)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
