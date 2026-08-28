#!/usr/bin/env python3
"""Validate authored content: the skill tree, its lessons and its gate scenarios.

    python -m scripts.validate_content

Exits non-zero if anything fails, so it can gate a build (spec v0.2 §14).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import tree_content  # noqa: E402
from app.content import ContentError  # noqa: E402


def _read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(kind: str) -> tuple[list[str], dict]:
    """Один вид дерева: контент, ошибки и цифры для сводки."""
    tree = tree_content.load_tree_file(kind)
    lessons = [_read(p) for p in tree_content.lesson_paths(kind)]
    gates = tree_content.load_gates_file(kind)["gates"]
    scenarios = [_read(p) for p in tree_content.gate_scenario_paths(kind)]
    exercises = [_read(p) for p in tree_content.exercise_paths(kind)]
    diagrams = [_read(p) for p in tree_content.diagram_paths(kind)]
    glossary = tree_content.load_glossary_file(kind)

    errors = tree_content.validate_tree(
        tree, lessons, gates, scenarios,
        root_block_id=tree_content.TREES[kind]["root"],
        exercises=exercises, glossary=glossary, diagrams=diagrams,
    )
    return errors, {
        "tree": tree, "lessons": lessons, "gates": gates, "scenarios": scenarios,
        "exercises": exercises, "diagrams": diagrams, "glossary": glossary,
    }



def check_audio_scripts() -> list[str]:
    """Сценарии обзоров: заглушки не публикуются, отставшие от урока — тоже.

    Проверяется здесь, а не в тестах аудио, потому что это свойство контента: в
    релиз не должен уехать обзор, который дословно зачитывает урок или рассказывает
    про его прошлую редакцию.
    """
    from app import tree_content
    from app.services import audio, audio_script

    problems: list[str] = []
    total = stale = 0
    for kind in tree_content.KINDS:
        for lesson in tree_content.tree_content(kind)["lessons"].values():
            path = audio.script_path(lesson)
            if not path.exists():
                continue
            total += 1
            if audio.load_script(lesson) is None:
                stale += 1
                continue
            script = json.loads(path.read_text(encoding="utf-8"))
            provider = script["generator"]["provider"]
            if provider == "mock":
                problems.append(f"{lesson['id']}: обзор-заглушка (provider=mock)")
                continue
            for problem in audio_script.validate_script(script["turns"], lesson):
                problems.append(f"{lesson['id']}: {problem}")

    print(f"\nОбзоров: {total} (устарело к тексту урока: {stale})")
    return problems

def main() -> int:
    product_errors, product = check("product")
    sd_errors, sd = check("system_design")
    tree = product["tree"]
    lessons = product["lessons"]
    gates = product["gates"]
    scenarios = product["scenarios"]

    roles_doc = tree_content.load_roles_file()

    errors = product_errors + tree_content.validate_roles(roles_doc, tree)
    errors += [f"system_design: {error}" for error in sd_errors]
    if errors:
        print(f"FAIL {len(errors)} problem(s):")
        for error in errors:
            print(f"   - {error}")
        return 1

    lessons_by_block: Counter[str] = Counter(item["blockId"] for item in lessons)
    published = [b for b in tree["blocks"] if b["status"] == "published"]

    for block in tree["blocks"]:
        mark = "ok  " if block["status"] == "published" else "soon"
        print(
            f"{mark} {block['id']:<3} {block['title']:<28} "
            f"{len(block['nodes'])} узлов, {lessons_by_block.get(block['id'], 0)} уроков"
        )

    print()
    print(f"Блоков: {len(tree['blocks'])} ({len(published)} опубликовано)")
    print(f"Узлов: {sum(len(b['nodes']) for b in tree['blocks'])}")
    print(f"Уроков: {len(lessons)}  Гейтов: {len(gates)}  Сценариев: {len(scenarios)}")
    print(f"QA-фикстур: {sum(len(s['qaSubmissions']) for s in scenarios)}")
    specialised = [r for r in roles_doc["roles"] if r["key"] != "product_manager"]
    print(
        f"Ролей: {len(roles_doc['roles'])} "
        f"(узлов в специализированных: {min(len(r['nodeIds']) for r in specialised)}"
        f"–{max(len(r['nodeIds']) for r in specialised)})"
    )
    print()
    sd_tree = sd["tree"]
    sd_published = [b for b in sd_tree["blocks"] if b["status"] == "published"]
    print()
    print(f"System Design: блоков {len(sd_tree['blocks'])} ({len(sd_published)} опубликовано), "
          f"узлов {sum(len(b['nodes']) for b in sd_tree['blocks'])}")
    print(f"Уроков: {len(sd['lessons'])}  Упражнений: {len(sd['exercises'])}  "
          f"Сценариев: {len(sd['scenarios'])}")
    print(f"Терминов: {len(sd['glossary']['terms'])}  Схем: {len(sd['diagrams'])}")
    audio_problems = check_audio_scripts()
    if audio_problems:
        print()
        for problem in audio_problems[:20]:
            print(f"  ! {problem}")
        if len(audio_problems) > 20:
            print(f"  ... и ещё {len(audio_problems) - 20}")
        print("\nОбзоры не проходят проверку — контент невалиден.")
        return 1

    print()
    print("Графы разблокировки ацикличны, всё достижимо из "
          f"{tree_content.TREES['product']['root']} и {tree_content.TREES['system_design']['root']}. "
          "Контент валиден.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContentError as exc:
        print(exc)
        raise SystemExit(1) from exc
