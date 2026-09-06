"""Skill-tree content: blocks, nodes, lessons and gates (spec v0.2 §6, §8).

Lives in validated JSON next to the scenario library rather than in the database.
Scenarios are seeded into Postgres because an attempt must keep the exact text it was
scored against; tree structure and lessons carry no such obligation — they are read-only
reference data, so a file plus a cache is the whole storage story.

Nothing here is model-generated. Lessons are authored (spec v0.2 §1, invariant 6).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from app.config import settings
from app.content import ContentError
from app.i18n_content import AUTHORED_LANGUAGE, apply_overlay

# Two trees share one grammar (spec SD §1): the product map and System Design. Each
# has its own directory and its own single entry point — everything must be reachable
# from it, or a learner could see a block on the map that no route ever opens.
TREES: dict[str, dict[str, str]] = {
    "product": {"dir": "tree", "root": "D1"},
    "system_design": {"dir": "system-design", "root": "DS1"},
}
KINDS = tuple(TREES)
DEFAULT_KIND = "product"

# Kept for callers that predate the second tree.
ROOT_BLOCK_ID = TREES[DEFAULT_KIND]["root"]


def _schema(name: str) -> dict[str, Any]:
    return json.loads((settings.content_dir / name).read_text(encoding="utf-8"))


def _without_min_length(node: Any) -> Any:
    """Схема без нижних границ длины.

    `minLength` — правило для автора («не пиши описание варианта одним словом»), а
    не свойство данных. Английский законно короче русского: «Согласиться на 99.95%.
    Ноль недель.» — 35 знаков, "Agree to 99.95%. Zero weeks." — 28. Требовать от
    перевода добрать до тридцати значит просить дописать воды.

    `maxLength` остаётся: это ограничение продукта — текст обязан поместиться.
    """
    if isinstance(node, dict):
        return {
            key: _without_min_length(value)
            for key, value in node.items()
            if key != "minLength"
        }
    if isinstance(node, list):
        return [_without_min_length(item) for item in node]
    return node


def _for_language(schema: dict[str, Any], language: str) -> dict[str, Any]:
    return schema if language == AUTHORED_LANGUAGE else _without_min_length(schema)


@lru_cache
def tree_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("tree.schema.json"), language)


@lru_cache
def lesson_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("lesson.schema.json"), language)


@lru_cache
def gate_scenario_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("gate-scenario.schema.json"), language)


@lru_cache
def exercise_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("exercise.schema.json"), language)


@lru_cache
def glossary_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("glossary.schema.json"), language)


@lru_cache
def diagram_schema(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    return _for_language(_schema("diagram.schema.json"), language)


def _tree_dir(kind: str = DEFAULT_KIND) -> Path:
    return settings.content_dir / TREES[kind]["dir"]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def overlay_path(path: Path, language: str) -> Path:
    """Где лежит перевод этого файла: то же относительное имя под `i18n/<язык>`."""
    return settings.content_dir / "i18n" / language / path.relative_to(settings.content_dir)


def _localised(path: Path, doc_kind: str, language: str) -> dict[str, Any]:
    """Авторский файл с наложенным переводом, если он есть и не устарел.

    Отсутствие перевода — не ошибка: файл показывается на языке оригинала. Так
    частично переведённый корпус работает, а не падает.
    """
    document = _read(path)
    if language == AUTHORED_LANGUAGE:
        return document
    candidate = overlay_path(path, language)
    overlay = _read(candidate) if candidate.exists() else None
    return apply_overlay(doc_kind, document, overlay, language)


def load_tree_file(
    kind: str = DEFAULT_KIND, language: str = AUTHORED_LANGUAGE
) -> dict[str, Any]:
    return _localised(_tree_dir(kind) / "tree.json", "tree", language)


def load_gates_file(kind: str = DEFAULT_KIND) -> dict[str, Any]:
    path = _tree_dir(kind) / "gates.json"
    return _read(path) if path.exists() else {"gates": []}


def lesson_paths(kind: str = DEFAULT_KIND) -> list[Path]:
    return sorted((_tree_dir(kind) / "lessons").glob("*.json"))


def gate_scenario_paths(kind: str = DEFAULT_KIND) -> list[Path]:
    return sorted((_tree_dir(kind) / "scenarios").glob("*.json"))


def exercise_paths(kind: str = DEFAULT_KIND) -> list[Path]:
    return sorted((_tree_dir(kind) / "exercises").glob("*.json"))


def diagram_paths(kind: str = DEFAULT_KIND) -> list[Path]:
    return sorted((_tree_dir(kind) / "diagrams").glob("*.json"))


def load_glossary_file(
    kind: str = DEFAULT_KIND, language: str = AUTHORED_LANGUAGE
) -> dict[str, Any]:
    path = _tree_dir(kind) / "glossary.json"
    if not path.exists():
        return {"version": 1, "terms": []}
    return _localised(path, "glossary", language)


# --- Validation --------------------------------------------------------------


def _schema_errors(validator: Draft7Validator, document: dict[str, Any]) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(document)
    ]


def validate_tree(
    tree: dict[str, Any],
    lessons: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
    *,
    root_block_id: str = ROOT_BLOCK_ID,
    exercises: list[dict[str, Any]] | None = None,
    glossary: dict[str, Any] | None = None,
    diagrams: list[dict[str, Any]] | None = None,
    language: str = AUTHORED_LANGUAGE,
) -> list[str]:
    """Structural rules the JSON schemas cannot express on their own."""
    errors = _schema_errors(Draft7Validator(tree_schema(language)), tree)
    if errors:
        return errors

    blocks = {block["id"]: block for block in tree["blocks"]}
    domain_keys = {domain["key"] for domain in tree["domains"]}
    lessons_by_block: dict[str, list[dict[str, Any]]] = {}
    node_ids: set[str] = set()

    for block in tree["blocks"]:
        if block["domainKey"] not in domain_keys:
            errors.append(f"{block['id']}: unknown domainKey '{block['domainKey']}'")
        for prerequisite in block["prerequisiteBlockIds"]:
            if prerequisite not in blocks:
                errors.append(f"{block['id']}: unknown prerequisite '{prerequisite}'")
        for node in block["nodes"]:
            if node["id"] in node_ids:
                errors.append(f"{block['id']}: duplicate node id '{node['id']}'")
            node_ids.add(node["id"])

    # The unlock graph must be a DAG, or a block could gate itself forever.
    errors.extend(_graph_errors(blocks, root_block_id))

    # System Design nodes must say which decision the PM makes (spec SD §2.5): the
    # procedural guard against the domain drifting into a course for engineers.
    if tree.get("kind") == "system_design":
        for block in tree["blocks"]:
            for node in block["nodes"]:
                if not node.get("pmDecision"):
                    errors.append(f"{node['id']}: node has no pmDecision")

    lesson_ids: set[str] = set()
    for lesson in lessons:
        for error in _schema_errors(Draft7Validator(lesson_schema(language)), lesson):
            errors.append(f"lesson {lesson.get('id', '?')}: {error}")
        if lesson["id"] in lesson_ids:
            errors.append(f"lesson {lesson['id']}: duplicate id")
        lesson_ids.add(lesson["id"])
        if lesson["nodeId"] not in node_ids:
            errors.append(f"lesson {lesson['id']}: unknown nodeId '{lesson['nodeId']}'")
        if lesson["blockId"] not in blocks:
            errors.append(f"lesson {lesson['id']}: unknown blockId '{lesson['blockId']}'")
        else:
            lessons_by_block.setdefault(lesson["blockId"], []).append(lesson)

    gates_by_block: dict[str, dict[str, Any]] = {}
    scenarios_by_id = {scenario["id"]: scenario for scenario in scenarios}
    for gate in gates:
        if gate["blockId"] not in blocks:
            errors.append(f"gate {gate['id']}: unknown blockId '{gate['blockId']}'")
        if gate["blockId"] in gates_by_block:
            errors.append(f"gate {gate['id']}: block already has a gate")
        gates_by_block[gate["blockId"]] = gate
        # Two scenarios minimum: with one, a retry becomes memorising which option
        # was right, which is the quiz this product must not become (spec §8).
        if len(gate["scenarioIds"]) < 2:
            errors.append(f"gate {gate['id']}: needs at least 2 scenarios")
        for scenario_id in gate["scenarioIds"]:
            if scenario_id not in scenarios_by_id:
                errors.append(f"gate {gate['id']}: unknown scenario '{scenario_id}'")

    lessons_by_id = {lesson["id"]: lesson for lesson in lessons}
    for scenario in scenarios:
        errors.extend(
            f"scenario {scenario['id']}: {error}"
            for error in validate_gate_scenario(scenario, lesson_ids, blocks, language)
        )
        # A gate never leans on a ring above its own: a first-ring exam must not
        # require second-ring knowledge (spec SD §2.4).
        own_tier = blocks.get(scenario["blockId"], {}).get("tier")
        for lesson_id in scenario.get("coveredLessonIds", []):
            covered = lessons_by_id.get(lesson_id)
            if covered is None or own_tier is None:
                continue
            covered_tier = blocks.get(covered["blockId"], {}).get("tier")
            if covered_tier is not None and covered_tier > own_tier:
                errors.append(
                    f"scenario {scenario['id']}: covers '{lesson_id}' from a higher ring "
                    f"(T{covered_tier} > T{own_tier})"
                )

    errors.extend(
        _content_errors(lessons, exercises or [], glossary or {"terms": []}, diagrams or [],
                        blocks, node_ids, language)
    )

    # A published block is one a learner can actually finish.
    for block in tree["blocks"]:
        if block["status"] != "published":
            continue
        if not lessons_by_block.get(block["id"]):
            errors.append(f"{block['id']}: published block has no lessons")
        if block["id"] not in gates_by_block:
            errors.append(f"{block['id']}: published block has no gate")
        covered_nodes = {
            lesson["nodeId"] for lesson in lessons_by_block.get(block["id"], [])
        }
        for node in block["nodes"]:
            if node["id"] not in covered_nodes:
                errors.append(f"{block['id']}: node '{node['id']}' has no lesson")

    return errors


def _graph_errors(blocks: dict[str, dict[str, Any]], root: str = ROOT_BLOCK_ID) -> list[str]:
    """Acyclic, and every block reachable from the root (spec §14)."""
    errors: list[str] = []

    colour: dict[str, int] = {}

    def visit(block_id: str) -> None:
        colour[block_id] = 1
        for prerequisite in blocks[block_id]["prerequisiteBlockIds"]:
            if prerequisite not in blocks:
                continue
            state = colour.get(prerequisite, 0)
            if state == 1:
                errors.append(f"unlock graph: cycle through '{prerequisite}'")
            elif state == 0:
                visit(prerequisite)
        colour[block_id] = 2

    for block_id in blocks:
        if colour.get(block_id, 0) == 0:
            visit(block_id)

    if root not in blocks:
        errors.append(f"unlock graph: root '{root}' is missing")
        return errors
    if blocks[root]["prerequisiteBlockIds"]:
        errors.append(f"unlock graph: root '{root}' must have no prerequisites")

    reachable = {root}
    changed = True
    while changed:
        changed = False
        for block_id, block in blocks.items():
            if block_id in reachable:
                continue
            prerequisites = block["prerequisiteBlockIds"]
            if prerequisites and all(p in reachable for p in prerequisites):
                reachable.add(block_id)
                changed = True
    for block_id in sorted(set(blocks) - reachable):
        errors.append(f"unlock graph: '{block_id}' is unreachable from {root}")
    return errors



def _content_errors(
    lessons: list[dict[str, Any]],
    exercises: list[dict[str, Any]],
    glossary: dict[str, Any],
    diagrams: list[dict[str, Any]],
    blocks: dict[str, Any],
    node_ids: set[str],
    language: str = AUTHORED_LANGUAGE,
) -> list[str]:
    """Glossary, exercises and diagrams — the rules from the System Design spec §8."""
    errors: list[str] = []

    if glossary.get("terms"):
        errors.extend(
            f"glossary: {error}"
            for error in _schema_errors(Draft7Validator(glossary_schema(language)), glossary)
        )
    terms: dict[str, dict[str, Any]] = {}
    for term in glossary.get("terms", []):
        if term["id"] in terms:
            errors.append(f"glossary: term '{term['id']}' defined twice")
        terms[term["id"]] = term
        if term["blockId"] not in blocks:
            errors.append(f"glossary {term['id']}: unknown blockId '{term['blockId']}'")

    diagram_ids: set[str] = set()
    for diagram in diagrams:
        errors.extend(
            f"diagram {diagram.get('id', '?')}: {error}"
            for error in _schema_errors(Draft7Validator(diagram_schema(language)), diagram)
        )
        diagram_ids.add(diagram["id"])
        declared = {node["id"] for node in diagram.get("nodes", [])}
        for edge in diagram.get("edges", []):
            for side in ("from", "to"):
                if edge.get(side) not in declared:
                    errors.append(
                        f"diagram {diagram['id']}: edge {side} '{edge.get(side)}' is not a node"
                    )

    lesson_ids = {lesson["id"] for lesson in lessons}
    exercise_ids: set[str] = set()
    for exercise in exercises:
        errors.extend(
            f"exercise {exercise.get('id', '?')}: {error}"
            for error in _schema_errors(Draft7Validator(exercise_schema(language)), exercise)
        )
        exercise_ids.add(exercise["id"])
        if exercise["nodeId"] not in node_ids:
            errors.append(f"exercise {exercise['id']}: unknown nodeId '{exercise['nodeId']}'")
        if exercise["blockId"] not in blocks:
            errors.append(f"exercise {exercise['id']}: unknown blockId '{exercise['blockId']}'")
        # An estimation exercise without an accepted range cannot be checked at all.
        if exercise["type"] == "estimation" and not exercise["acceptance"]:
            errors.append(f"exercise {exercise['id']}: estimation needs an acceptance range")
        for rule in exercise["acceptance"]:
            if rule["inputId"] not in {i["id"] for i in exercise["inputs"]}:
                errors.append(
                    f"exercise {exercise['id']}: acceptance for unknown input '{rule['inputId']}'"
                )

    marker = re.compile(r"\[\[([^\]|]+)\|")
    for lesson in lessons:
        for term_id in lesson.get("termIds", []):
            if term_id not in terms:
                errors.append(f"lesson {lesson['id']}: unknown term '{term_id}'")
        # Правило 8 спеки System Design: помеченное в тексте должно открываться.
        # Подчёркивание, ведущее в никуда, хуже отсутствия подчёркивания.
        declared = set(lesson.get("termIds", []))
        for section in lesson.get("sections", []):
            for block in section["blocks"]:
                fields = [block.get("text", "")]
                fields += block.get("items", [])
                fields += [cell for row in block.get("rows", []) for cell in row]
                for field in fields:
                    for marked in marker.findall(field or ""):
                        if marked not in terms:
                            errors.append(
                                f"lesson {lesson['id']}: text marks unknown term '{marked}'"
                            )
                        elif marked not in declared:
                            errors.append(
                                f"lesson {lesson['id']}: '{marked}' marked in text "
                                "but not in termIds"
                            )
        for diagram_id in lesson.get("diagramIds", []):
            if diagram_id not in diagram_ids:
                errors.append(f"lesson {lesson['id']}: unknown diagram '{diagram_id}'")
        for reference in lesson.get("crossRefs", []):
            if reference not in lesson_ids:
                errors.append(f"lesson {lesson['id']}: crossRef to unknown lesson '{reference}'")
        if lesson.get("exerciseId") and lesson["exerciseId"] not in exercise_ids:
            errors.append(f"lesson {lesson['id']}: unknown exercise '{lesson['exerciseId']}'")
        sections = lesson.get("sections")
        if sections:
            order = [section["kind"] for section in sections]
            expected = ["question", "cost", "substance", "example", "limits", "takeaway"]
            if order != expected:
                errors.append(
                    f"lesson {lesson['id']}: sections out of order — {', '.join(order)}"
                )

    for term in glossary.get("terms", []):
        source = term.get("sourceLessonId")
        if source and source not in lesson_ids:
            errors.append(f"glossary {term['id']}: unknown sourceLessonId '{source}'")

    return errors


def validate_gate_scenario(
    scenario: dict[str, Any],
    lesson_ids: set[str],
    blocks: dict[str, Any],
    language: str = AUTHORED_LANGUAGE,
) -> list[str]:
    """Schema, the v0.1 editorial rules, plus the lesson links v0.2 adds."""
    errors = _schema_errors(Draft7Validator(gate_scenario_schema(language)), scenario)
    if errors:
        return errors

    from app.content import validate_scenario_rules

    errors.extend(validate_scenario_rules(scenario))

    if scenario["blockId"] not in blocks:
        errors.append(f"unknown blockId '{scenario['blockId']}'")
    for lesson_id in scenario["coveredLessonIds"]:
        if lesson_id not in lesson_ids:
            errors.append(f"coveredLessonIds: unknown lesson '{lesson_id}'")

    rubric = scenario["rubric"]
    for index, signal in enumerate(rubric["positiveSignals"]):
        if signal["lessonId"] not in lesson_ids:
            errors.append(f"positiveSignals[{index}]: unknown lesson '{signal['lessonId']}'")
    for index, entry in enumerate(rubric["remediation"]):
        if entry["lessonId"] not in lesson_ids:
            errors.append(f"remediation[{index}]: unknown lesson '{entry['lessonId']}'")

    # Remediation is what makes a failed gate actionable; every gap the rubric can
    # detect needs somewhere to send the learner.
    remediated = {entry["lessonId"] for entry in rubric["remediation"]}
    for lesson_id in scenario["coveredLessonIds"]:
        if lesson_id not in remediated:
            errors.append(f"remediation: no entry for covered lesson '{lesson_id}'")
    return errors


# --- Loading -----------------------------------------------------------------


@lru_cache
def load_roles_file() -> dict[str, Any]:
    return json.loads((_tree_dir() / "roles.json").read_text(encoding="utf-8"))


def validate_roles(roles_doc: dict[str, Any], tree: dict[str, Any]) -> list[str]:
    """Role overlays name real nodes, and Product Manager covers the whole map.

    The overlays are read off the source diagram, so the thing that can rot here is the
    link to our own tree: a renamed node would silently drop out of a role.
    """
    errors: list[str] = []
    known = {node["id"] for block in tree["blocks"] for node in block["nodes"]}
    seen_keys: set[str] = set()
    for role in roles_doc.get("roles", []):
        key = role.get("key", "?")
        if key in seen_keys:
            errors.append(f"roles: duplicate key {key}")
        seen_keys.add(key)
        if not role.get("title"):
            errors.append(f"roles/{key}: no title")
        node_ids = role.get("nodeIds", [])
        if len(node_ids) != len(set(node_ids)):
            errors.append(f"roles/{key}: repeated nodeIds")
        for node_id in node_ids:
            if node_id not in known:
                errors.append(f"roles/{key}: unknown node {node_id}")
    if "product_manager" not in seen_keys:
        errors.append("roles: product_manager is missing — it is the role that spans the map")
    else:
        pm = next(r for r in roles_doc["roles"] if r["key"] == "product_manager")
        if set(pm.get("nodeIds", [])) != known:
            errors.append("roles/product_manager: must cover every node on the map")
    return errors


@lru_cache
def tree_content(
    kind: str = DEFAULT_KIND, language: str = AUTHORED_LANGUAGE
) -> dict[str, Any]:
    """Validated tree, lessons, gates, scenarios and — for System Design — the
    exercises, glossary and diagrams that go with them.

    `language` выбирает наложение перевода. Структура, рубрики и QA-фикстуры от него
    не зависят — переводится только то, что читает человек.
    """
    tree = load_tree_file(kind, language)
    lessons = [_localised(p, "lesson", language) for p in lesson_paths(kind)]
    gates = load_gates_file(kind)["gates"]
    scenarios = [_localised(p, "scenario", language) for p in gate_scenario_paths(kind)]
    exercises = [_localised(p, "exercise", language) for p in exercise_paths(kind)]
    diagrams = [_localised(p, "diagram", language) for p in diagram_paths(kind)]
    glossary = load_glossary_file(kind, language)

    errors = validate_tree(
        tree, lessons, gates, scenarios,
        root_block_id=TREES[kind]["root"],
        exercises=exercises, glossary=glossary, diagrams=diagrams,
        language=language,
    )
    if errors:
        raise ContentError(f"Invalid {kind} tree content:\n  " + "\n  ".join(errors))

    lessons_by_block: dict[str, list[dict[str, Any]]] = {}
    for lesson in sorted(lessons, key=lambda item: (item["nodeId"], item["order"])):
        lessons_by_block.setdefault(lesson["blockId"], []).append(lesson)

    return {
        "kind": kind,
        "language": language,
        "root": TREES[kind]["root"],
        "tree": tree,
        "blocks": {block["id"]: block for block in tree["blocks"]},
        "domains": tree["domains"],
        "tiers": tree["tiers"],
        "lessons": {lesson["id"]: lesson for lesson in lessons},
        "lessons_by_block": lessons_by_block,
        "gates": {gate["id"]: gate for gate in gates},
        "gate_by_block": {gate["blockId"]: gate for gate in gates},
        "scenarios": {scenario["id"]: scenario for scenario in scenarios},
        "exercises": {exercise["id"]: exercise for exercise in exercises},
        "exercise_by_node": {exercise["nodeId"]: exercise for exercise in exercises},
        "diagrams": {diagram["id"]: diagram for diagram in diagrams},
        "glossary": {term["id"]: term for term in glossary.get("terms", [])},
    }


@lru_cache
def all_content(language: str = AUTHORED_LANGUAGE) -> dict[str, Any]:
    """Both trees merged for lookup by id.

    Ids are globally unique across the two trees (`D1` vs `DS1`), so services can keep
    asking for a block or a lesson without knowing which map it belongs to.
    """
    merged: dict[str, Any] = {
        key: {} for key in (
            "blocks", "lessons", "lessons_by_block", "gates", "gate_by_block",
            "scenarios", "exercises", "exercise_by_node", "diagrams", "glossary",
            "kind_of_block",
        )
    }
    merged["trees"] = {}
    for kind in KINDS:
        content = tree_content(kind, language)
        merged["trees"][kind] = content
        for key in (
            "blocks", "lessons", "lessons_by_block", "gates", "gate_by_block",
            "scenarios", "exercises", "exercise_by_node", "diagrams", "glossary",
        ):
            merged[key].update(content[key])
        for block_id in content["blocks"]:
            merged["kind_of_block"][block_id] = kind
    return merged


def kinds() -> tuple[str, ...]:
    return KINDS


def blocks_of(kind: str, language: str = AUTHORED_LANGUAGE) -> list[dict[str, Any]]:
    return tree_content(kind, language)["tree"]["blocks"]


def all_blocks() -> list[dict[str, Any]]:
    return [block for kind in KINDS for block in blocks_of(kind)]


def block(block_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["blocks"].get(block_id)


def kind_of_block(block_id: str) -> str | None:
    return all_content()["kind_of_block"].get(block_id)


def lesson(lesson_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["lessons"].get(lesson_id)


def lessons_for_block(
    block_id: str, language: str = AUTHORED_LANGUAGE
) -> list[dict[str, Any]]:
    return all_content(language)["lessons_by_block"].get(block_id, [])


def gate(gate_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["gates"].get(gate_id)


def gate_for_block(
    block_id: str, language: str = AUTHORED_LANGUAGE
) -> dict[str, Any] | None:
    return all_content(language)["gate_by_block"].get(block_id)


def scenario(scenario_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["scenarios"].get(scenario_id)


def exercise(exercise_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["exercises"].get(exercise_id)


def exercise_for_node(
    node_id: str, language: str = AUTHORED_LANGUAGE
) -> dict[str, Any] | None:
    return all_content(language)["exercise_by_node"].get(node_id)


def diagram(diagram_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["diagrams"].get(diagram_id)


def glossary_terms(
    kind: str = "system_design", language: str = AUTHORED_LANGUAGE
) -> list[dict[str, Any]]:
    return list(tree_content(kind, language)["glossary"].values())


def glossary_term(term_id: str, language: str = AUTHORED_LANGUAGE) -> dict[str, Any] | None:
    return all_content(language)["glossary"].get(term_id)


def dependents(block_id: str) -> list[str]:
    """Blocks whose unlock depends on this one."""
    return [
        candidate["id"]
        for candidate in all_blocks()
        if block_id in candidate["prerequisiteBlockIds"]
    ]
