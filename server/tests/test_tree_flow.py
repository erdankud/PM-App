"""The v0.2 loop end to end: tree → lessons → gate → unlock (spec v0.2 §14)."""

from __future__ import annotations

import uuid

from conftest import block_lessons, onboard, read_all_lessons, start_gate

from app import tree_content
from app.worker import run_once

STRONG = (
    "Пишут в основном сотрудники, а платит владелец — это надо разделить до того, как "
    "что-то строить. Четыре письма про отчёты пришли с одного аккаунта, то есть это один "
    "голос, а не крупнейшая тема. Среднее 3,1 обмена ничего не описывает: разрежу по "
    "распределению и посмотрю, какая доля аккаунтов вообще делает обмены. Гипотеза: "
    "владельцы уходят, потому что сотрудники переспрашивают их вручную. Скрипт перепишу "
    "на прошлое поведение и буду измерять долю обменов без сообщения владельцу."
)
WEAK = "Надо сделать отчёты, про них больше всего пишут в поддержку."


def drain() -> None:
    while run_once():
        pass


def submit(client, headers, challenge, option_index: int, rationale: str):
    attempt_id = challenge["attempt"]["attemptId"]
    for card in challenge["scenario"]["evidenceCards"][: 4 if option_index == 0 else 1]:
        client.post(
            f"/v1/attempts/{attempt_id}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )
    return client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "selectedOptionId": challenge["scenario"]["decisionOptions"][option_index]["id"],
            "rationale": rationale,
        },
    )


def pass_gate(client, headers) -> dict:
    read_all_lessons(client, headers, "D1")
    challenge = start_gate(client, headers)
    submit(client, headers, challenge, 0, STRONG)
    drain()
    return client.get(
        f"/v1/attempts/{challenge['attempt']['attemptId']}/feedback", headers=headers
    ).json()


# --- The map -----------------------------------------------------------------


def test_new_user_sees_the_whole_map_with_one_block_open(client):
    headers, _ = onboard(client)
    tree = client.get("/v1/tree", headers=headers).json()

    assert len(tree["blocks"]) == 18
    assert sum(b["nodeCount"] for b in tree["blocks"]) == 71
    assert tree["sourceAttribution"]

    open_blocks = [b["id"] for b in tree["blocks"] if b["status"] != "locked"]
    assert open_blocks == ["D1"]
    # Everything else is visible, not hidden: the map is the promise (spec §2).
    assert all(b["title"] for b in tree["blocks"])


def test_locked_block_opens_and_explains_itself(client):
    headers, _ = onboard(client)
    detail = client.get("/v1/blocks/V1", headers=headers).json()

    assert detail["block"]["status"] == "locked"
    assert detail["gateAvailable"] is False
    assert detail["gateBlockedReason"] == "locked"
    assert detail["block"]["prerequisiteBlockIds"] == ["D1"]
    assert len(detail["nodes"]) == 4


def test_unwritten_block_is_marked_rather_than_hidden(client):
    """Counted against the content itself, so publishing a block does not break this."""
    headers, _ = onboard(client)
    tree = client.get("/v1/tree", headers=headers).json()
    blocks = tree_content.tree_content()["tree"]["blocks"]
    expected = {b["id"] for b in blocks if b["status"] == "coming_soon"}

    coming = {b["id"] for b in tree["blocks"] if b["contentStatus"] == "coming_soon"}
    assert coming == expected
    assert all(
        b["lessonsTotal"] == 0 for b in tree["blocks"] if b["id"] in coming
    ), "a block with no lessons written must report none"


# --- Lessons -----------------------------------------------------------------


def test_lesson_completion_is_idempotent_and_awards_xp_once(client):
    headers, _ = onboard(client)
    lesson_id = block_lessons("D1")[0]

    first = client.post(f"/v1/lessons/{lesson_id}/complete", headers=headers).json()
    second = client.post(f"/v1/lessons/{lesson_id}/complete", headers=headers).json()

    assert first["xpAwarded"] == 10
    assert second["xpAwarded"] == 0
    assert second["lessonsCompleted"] == 1
    assert second["blockStatus"] == "in_progress"


def test_block_becomes_gate_ready_only_when_every_lesson_is_read(client):
    headers, _ = onboard(client)
    lessons = block_lessons("D1")

    for lesson_id in lessons[:-1]:
        result = client.post(f"/v1/lessons/{lesson_id}/complete", headers=headers).json()
        assert result["gateAvailable"] is False

    final = client.post(f"/v1/lessons/{lessons[-1]}/complete", headers=headers).json()
    assert final["gateAvailable"] is True
    assert final["blockStatus"] == "gate_ready"


def test_lesson_payload_carries_its_content_and_the_next_step(client):
    headers, _ = onboard(client)
    lesson = client.get(f"/v1/lessons/{block_lessons('D1')[0]}", headers=headers).json()

    assert lesson["keyTakeaway"]
    assert len(lesson["blocks"]) >= 3
    assert {b["type"] for b in lesson["blocks"]} <= {
        "paragraph", "list", "example", "model_card", "callout"
    }
    assert lesson["nextLessonId"]


# --- The gate ----------------------------------------------------------------


def test_gate_start_is_refused_while_lessons_remain(client):
    headers, _ = onboard(client)
    client.post(f"/v1/lessons/{block_lessons('D1')[0]}/complete", headers=headers)

    # The UI hides the button; this is the guarantee that the button is not the rule.
    response = client.post("/v1/gates/gate-d1/start", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "block_not_ready"


def test_passing_a_gate_unlocks_the_next_block_and_awards_xp(client):
    headers, _ = onboard(client)
    feedback = pass_gate(client, headers)

    assert feedback["passed"] is True
    assert feedback["feedback"]["score"] >= feedback["passThreshold"]
    assert "V1" in feedback["unlockedBlockIds"]

    tree = client.get("/v1/tree", headers=headers).json()
    statuses = {b["id"]: b["status"] for b in tree["blocks"]}
    assert statuses["D1"] == "passed"
    assert statuses["V1"] == "available"
    assert statuses["D2"] == "available"  # X2 opens after X1 of the same domain
    assert statuses["R1"] == "locked"     # still needs V1

    progress = client.get("/v1/progress", headers=headers).json()
    assert progress["blocksPassed"] == 1
    assert progress["totalXp"] >= 60 + 10 * len(block_lessons("D1"))


def test_failing_a_gate_keeps_xp_and_points_at_specific_lessons(client):
    headers, _ = onboard(client)
    read_all_lessons(client, headers, "D1")
    before = client.get("/v1/progress", headers=headers).json()["totalXp"]

    challenge = start_gate(client, headers)
    submit(client, headers, challenge, 1, WEAK)
    drain()
    feedback = client.get(
        f"/v1/attempts/{challenge['attempt']['attemptId']}/feedback", headers=headers
    ).json()

    assert feedback["passed"] is False
    assert feedback["remediation"], "a failed gate must say where to go back to"
    known = set(tree_content.tree_content()["lessons"])
    assert all(item["lessonId"] in known for item in feedback["remediation"])
    assert all(item["lessonTitle"] for item in feedback["remediation"])

    after = client.get("/v1/progress", headers=headers).json()
    assert after["totalXp"] == before          # failure never costs XP
    assert after["blocksPassed"] == 0
    tree = client.get("/v1/tree", headers=headers).json()
    assert {b["id"]: b["status"] for b in tree["blocks"]}["D1"] == "gate_ready"


def test_a_retake_serves_a_different_scenario(client):
    headers, _ = onboard(client)
    read_all_lessons(client, headers, "D1")

    first = start_gate(client, headers)
    submit(client, headers, first, 1, WEAK)
    drain()
    second = start_gate(client, headers)

    assert second["scenario"]["id"] != first["scenario"]["id"]
    assert second["attemptIndex"] == 2


def test_passing_a_block_again_awards_nothing(client):
    headers, _ = onboard(client)
    pass_gate(client, headers)
    after_first = client.get("/v1/progress", headers=headers).json()["totalXp"]

    challenge = start_gate(client, headers)
    submit(client, headers, challenge, 0, STRONG)
    drain()

    assert client.get("/v1/progress", headers=headers).json()["totalXp"] == after_first


def test_choosing_an_option_without_reasoning_cannot_pass(client):
    """Evidence 15 + decision 25 caps at 40, below the 70 threshold (spec v0.2 §9)."""
    headers, _ = onboard(client)
    read_all_lessons(client, headers, "D1")
    challenge = start_gate(client, headers)
    submit(client, headers, challenge, 0, "Выберу первый вариант, он выглядит разумным.")
    drain()

    feedback = client.get(
        f"/v1/attempts/{challenge['attempt']['attemptId']}/feedback", headers=headers
    ).json()
    assert feedback["passed"] is False


def test_a_defensible_alternative_is_scored_on_its_reasoning(client):
    """Several answers may be defended (§2).

    The ceiling is a content property and is asserted directly; where a given answer
    lands is the evaluator's job, and under EVALUATOR_PROVIDER=mock that is a keyword
    stub, so this checks the gap over a weak answer rather than a fixed band.
    """
    headers, _ = onboard(client)
    read_all_lessons(client, headers, "D1")
    challenge = start_gate(client, headers)
    alternative = next(
        index
        for index, option in enumerate(challenge["scenario"]["decisionOptions"])
        if option["id"] == "ship-notifications"
    )
    submit(
        client, headers, challenge, alternative,
        "Обмен сменами — самая плотная тема, уведомления дешёвы и обратимы. Признаю, что "
        "опознал тему по частоте слова, а не по разбору, и что среднее 3,1 может скрывать "
        "сегмент, которого это не касается. Поэтому выкачу и буду измерять отток отдельно "
        "по тем, кто делает обмены, и по тем, кто нет: если у второй группы ничего не "
        "изменится, гипотеза неверна и я разложу обратную связь как следует.",
    )
    drain()
    feedback = client.get(
        f"/v1/attempts/{challenge['attempt']['attemptId']}/feedback", headers=headers
    ).json()
    alternative_score = feedback["feedback"]["score"]

    # The option itself must leave room to pass: evidence 15 + its own points + a full
    # 60 for reasoning has to clear the threshold, or the gate is a single-answer quiz.
    scenario = tree_content.tree_content()["scenarios"][challenge["scenario"]["id"]]
    points = next(
        o["decisionPoints"]
        for o in scenario["decisionOptions"]
        if o["id"] == "ship-notifications"
    )
    assert 15 + points + 60 >= feedback["passThreshold"]

    weak_headers, _ = onboard(client)
    read_all_lessons(client, weak_headers, "D1")
    weak_challenge = start_gate(client, weak_headers)
    submit(client, weak_headers, weak_challenge, 1, WEAK)
    drain()
    weak_score = client.get(
        f"/v1/attempts/{weak_challenge['attempt']['attemptId']}/feedback",
        headers=weak_headers,
    ).json()["feedback"]["score"]
    assert alternative_score > weak_score + 15


# --- Ownership ---------------------------------------------------------------


def test_another_users_attempt_is_not_reachable(client):
    owner_headers, _ = onboard(client)
    read_all_lessons(client, owner_headers, "D1")
    challenge = start_gate(client, owner_headers)

    other_headers, _ = onboard(client)
    attempt_id = challenge["attempt"]["attemptId"]
    assert client.get(f"/v1/attempts/{attempt_id}/feedback", headers=other_headers).status_code == 404
    assert client.put(
        f"/v1/attempts/{attempt_id}/draft", headers=other_headers, json={"rationale": "x"}
    ).status_code == 404


def test_unknown_ids_are_404_not_500(client):
    headers, _ = onboard(client)
    assert client.get("/v1/blocks/ZZ", headers=headers).status_code == 404
    assert client.get("/v1/lessons/nope", headers=headers).status_code == 404
    assert client.post("/v1/gates/nope/start", headers=headers).status_code == 404


# --- Content invariants ------------------------------------------------------


def test_unlock_graph_is_acyclic_and_fully_reachable():
    content = tree_content.tree_content()
    blocks = content["blocks"]
    errors = tree_content._graph_errors(blocks)
    assert errors == []


def test_every_gate_has_at_least_two_scenarios():
    for gate in tree_content.tree_content()["gates"].values():
        assert len(gate["scenarioIds"]) >= 2
