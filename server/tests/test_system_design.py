"""Домен System Design: два дерева, упражнения, глоссарий, схемы.

Проверяются те утверждения спеки домена (§10), которые можно проверить кодом:
вход независим от основного дерева, упражнения формирующие, эталон приходит всегда,
гейт не зависит от упражнений, дельта уходит в восьмую компетенцию.
"""

from __future__ import annotations

from conftest import onboard

from app import tree_content
from app.worker import run_once

def drain() -> None:
    while run_once():
        pass


def test_two_trees_are_offered(client):
    headers, _ = onboard(client)
    trees = client.get("/v1/trees", headers=headers).json()["trees"]
    kinds = {tree["kind"] for tree in trees}
    assert kinds == {"product", "system_design"}
    for tree in trees:
        assert tree["blocksTotal"] == 18


def test_system_design_is_open_from_day_one(client):
    """Фон у людей разный: человек из разработки может начать отсюда (спека SD §2.3)."""
    headers, _ = onboard(client)
    tree = client.get("/v1/tree/system_design", headers=headers).json()
    assert tree["kind"] == "system_design"
    statuses = {block["id"]: block["status"] for block in tree["blocks"]}
    assert statuses["DS1"] == "available"
    # Ни один блок основного дерева при этом не сдан.
    product = client.get("/v1/tree/product", headers=headers).json()
    assert all(block["status"] != "passed" for block in product["blocks"])


def test_unknown_tree_kind_is_rejected(client):
    headers, _ = onboard(client)
    assert client.get("/v1/tree/marketing", headers=headers).status_code == 404


def test_lesson_carries_sections_terms_and_diagram(client):
    headers, _ = onboard(client)
    lesson = client.get("/v1/lessons/ds1-n1-l1", headers=headers).json()
    assert [section["kind"] for section in lesson["sections"]] == [
        "question", "cost", "substance", "example", "limits", "takeaway",
    ]
    assert lesson["terms"], "в уроке должны быть термины глоссария"
    assert lesson["diagrams"], "схема едет вместе с уроком"
    diagram = lesson["diagrams"][0]
    assert diagram["textDescription"].startswith("Схема")
    assert all(node["type"] in {
        "client", "service", "store", "cache", "queue", "external", "boundary", "actor"
    } for node in diagram["nodes"])


def test_reading_a_lesson_marks_its_terms_as_seen(client):
    headers, _ = onboard(client)
    before = client.get("/v1/glossary", headers=headers).json()["terms"]
    assert not any(term["seen"] for term in before)

    client.get("/v1/lessons/ds1-n1-l1", headers=headers)
    after = {term["id"]: term for term in client.get("/v1/glossary", headers=headers).json()["terms"]}
    lesson = tree_content.lesson("ds1-n1-l1")
    for term_id in lesson["termIds"]:
        assert after[term_id]["seen"], term_id


def test_glossary_searches_both_languages(client):
    headers, _ = onboard(client)
    russian = client.get("/v1/glossary", headers=headers, params={"q": "индекс"}).json()
    english = client.get("/v1/glossary", headers=headers, params={"q": "index"}).json()
    assert russian["terms"] and english["terms"]
    assert {t["id"] for t in english["terms"]} & {t["id"] for t in russian["terms"]}


def test_exercise_returns_the_reference_even_for_an_empty_answer(client):
    """Формирующее упражнение: разбор нужен именно тому, кто не знал, как подступиться."""
    headers, _ = onboard(client)
    exercise_id = tree_content.tree_content("system_design")["exercises"]["ex-ds1-1"]["id"]
    empty = client.post(
        f"/v1/exercises/{exercise_id}/submit", headers=headers, json={"values": {}}
    ).json()
    assert empty["referenceReasoningBlocks"]


def test_exercise_does_not_touch_xp_or_gate_availability(client):
    headers, _ = onboard(client)
    before = client.get("/v1/progress", headers=headers).json()

    client.post("/v1/exercises/ex-ds1-1/submit", headers=headers, json={"values": {}})

    after = client.get("/v1/progress", headers=headers).json()
    assert after["totalXp"] == before["totalXp"]
    block = client.get("/v1/blocks/DS1", headers=headers).json()
    assert block["gateAvailable"] is False


def _read_all_ds1(client, headers) -> None:
    for lesson in tree_content.lessons_for_block("DS1"):
        client.post(f"/v1/lessons/{lesson['id']}/complete", headers=headers)


def test_gate_opens_after_lessons_and_passing_unlocks_the_next_blocks(client):
    headers, _ = onboard(client)
    _read_all_ds1(client, headers)

    block = client.get("/v1/blocks/DS1", headers=headers).json()
    assert block["gateAvailable"] is True

    challenge = client.post("/v1/gates/gate-ds1/start", headers=headers).json()
    attempt_id = challenge["attempt"]["attemptId"]
    scenario = challenge["scenario"]
    # Веса опций клиенту не отдаются — увидеть их до решения значило бы получить
    # ответ. Эталон берём из контента на сервере.
    authored = tree_content.scenario(scenario["id"])
    strong = next(qa for qa in authored["qaSubmissions"] if qa["label"] == "strong")
    for card in scenario["evidenceCards"]:
        client.post(
            f"/v1/attempts/{attempt_id}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )
    submitted = client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={"selectedOptionId": strong["optionId"], "rationale": strong["rationale"]},
    )
    assert submitted.status_code == 200
    drain()

    feedback = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    assert feedback["passed"] is True

    tree = client.get("/v1/tree/system_design", headers=headers).json()
    statuses = {block["id"]: block["status"] for block in tree["blocks"]}
    assert statuses["DS1"] == "passed"
    # Шапка блока в источнике обещает открыть DS2 и IN1.
    assert statuses["DS2"] != "locked"
    assert statuses["IN1"] != "locked"


def test_progress_shows_eight_competencies(client):
    headers, _ = onboard(client)
    progress = client.get("/v1/progress", headers=headers).json()
    keys = {skill["key"] for skill in progress["skills"]}
    assert "system_design" in keys
    assert len(keys) == 8


def test_typed_exercises_are_answerable(client):
    """Размеченное упражнение должно приниматься эталонным ответом.

    Это защита от расхождения между `acceptance` и разбором: интервал, в который
    не попадает собственный эталон, проверяет не понимание, а опечатку автора.
    """
    from app.tree_content import tree_content

    headers, _ = onboard(client)
    content = tree_content("system_design")
    typed = [e for e in content["exercises"].values() if e["acceptance"]]
    assert len(typed) >= 50, "разметка упражнений пропала — проверьте scripts/type_exercises.py"

    for exercise in typed:
        ids = {field["id"] for field in exercise["inputs"]}
        values = {}
        for rule in exercise["acceptance"]:
            assert rule["inputId"] in ids, f"{exercise['id']}: приёмка без поля"
            if "expected" in rule:
                values[rule["inputId"]] = rule["expected"]
            else:
                values[rule["inputId"]] = str((rule["min"] + rule["max"]) / 2)

        response = client.post(
            f"/v1/exercises/{exercise['id']}/submit",
            json={"values": values},
            headers=headers,
        )
        assert response.status_code == 200, exercise["id"]
        body = response.json()
        assert all(item["withinRange"] for item in body["results"]), exercise["id"]
        # Формирующее упражнение возвращает разбор в любом случае.
        assert body["referenceReasoningBlocks"]


def test_choice_exercises_declare_their_options():
    """Поле выбора без вариантов — это поле ввода текста, которое притворяется выбором."""
    from app.tree_content import tree_content

    for exercise in tree_content("system_design")["exercises"].values():
        for field in exercise["inputs"]:
            if field["type"] == "choice":
                assert field.get("choices"), f"{exercise['id']}/{field['id']}"


def test_exercise_serves_the_diagram_its_prompt_refers_to(client):
    """«Дана схема» в условии означает, что схема приходит вместе с упражнением."""
    headers, _ = onboard(client)
    body = client.get("/v1/exercises/ex-ds1-1", headers=headers).json()
    referenced = {
        block["diagramId"] for block in body["promptBlocks"] if block["type"] == "diagram_ref"
    }
    assert referenced, "условие ссылается на схему «Полки»"
    assert {diagram["id"] for diagram in body["diagrams"]} == referenced
    # Описание словами строится из структуры — картинке это недоступно (спека SD §10).
    assert all(diagram["textDescription"] for diagram in body["diagrams"])


def test_lesson_blocks_keep_tables_and_diagram_references(client):
    """Таблица без строк и ссылка на схему без идентификатора рисуются пустым местом.

    Клиент читает `header`/`rows`/`diagramId`; если ответ их не несёт, урок теряет
    содержание молча — ошибки нет, просто пусто.
    """
    headers, _ = onboard(client)
    tables = diagram_refs = 0
    for lesson in tree_content.tree_content("system_design")["lessons"].values():
        raw = [block for section in lesson["sections"] for block in section["blocks"]]
        if not any(block["type"] in ("table", "diagram_ref") for block in raw):
            continue
        body = client.get(f"/v1/lessons/{lesson['id']}", headers=headers).json()
        served = [block for section in body["sections"] for block in section["blocks"]]
        for block in served:
            if block["type"] == "table":
                assert block["header"] and block["rows"] is not None, lesson["id"]
                tables += 1
            if block["type"] == "diagram_ref":
                assert block["diagramId"], lesson["id"]
                diagram_refs += 1
    assert tables and diagram_refs, "в контенте есть и таблицы, и схемы — проверять есть что"
