"""State transitions, ownership, idempotency and validation over the HTTP API."""

from __future__ import annotations

import uuid

from conftest import onboard, start_challenge

from app.db import SessionLocal
from app.models import ChallengeAttempt, LearningPathAssignment, XpLedgerEntry
from app.worker import run_once


def drain() -> int:
    """Process every queued evaluation. Other tests may have left work behind."""
    processed = 0
    while run_once():
        processed += 1
        assert processed < 50, "worker queue did not drain"
    return processed


VALID_RATIONALE = (
    "The funnel points at one step rather than the whole flow, so I would ship the "
    "cheap reversible fix first and measure step conversion weekly. The trade-off is "
    "that I am acting on a hypothesis rather than proof."
)


def _review_all_evidence(client, headers, challenge) -> None:
    for card in challenge["scenario"]["evidenceCards"]:
        client.post(
            f"/v1/attempts/{challenge['attempt']['attemptId']}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )


def _submit(client, headers, challenge, key: str | None = None):
    attempt_id = challenge["attempt"]["attemptId"]
    request_headers = dict(headers)
    if key:
        request_headers["Idempotency-Key"] = key
    return client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=request_headers,
        json={
            "selectedOptionId": challenge["scenario"]["decisionOptions"][0]["id"],
            "rationale": VALID_RATIONALE,
        },
    )


def test_onboarding_gates_today(client):
    auth = client.post(
        "/v1/auth/dev", json={"deviceId": f"gate-{uuid.uuid4()}"}
    ).json()
    headers = {"Authorization": f"Bearer {auth['accessToken']}"}
    assert client.get("/v1/today", headers=headers).status_code == 409


def test_complete_onboarding_requires_assessment(client):
    auth = client.post(
        "/v1/auth/dev", json={"deviceId": f"gate2-{uuid.uuid4()}"}
    ).json()
    headers = {"Authorization": f"Bearer {auth['accessToken']}"}
    response = client.patch(
        "/v1/me/profile", headers=headers, json={"completeOnboarding": True}
    )
    assert response.status_code == 409


def test_assessment_initialises_bounded_skill_baselines(client):
    headers, me = onboard(client)
    assert me["startingLevel"] in {"foundation", "developing", "advanced"}
    assert len(me["skills"]) == 6
    for skill in me["skills"]:
        assert 35 <= skill["score"] <= 65
    assert len(me["focusSkills"]) == 2


def test_today_is_stable_within_a_day(client):
    headers, _ = onboard(client)
    first = client.get("/v1/today", headers=headers).json()
    second = client.get("/v1/today", headers=headers).json()
    assert first["assignment"]["assignmentId"] == second["assignment"]["assignmentId"]
    assert first["localDate"] == second["localDate"]


def test_path_has_seven_distinct_scenarios(client):
    headers, _ = onboard(client)
    today = client.get("/v1/today", headers=headers).json()
    scenario_ids = [day["scenarioId"] for day in today["upcoming"]]
    assert len(scenario_ids) == 7
    assert len(set(scenario_ids)) == 7


def test_challenge_payload_withholds_rubric_and_consequences(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    scenario = challenge["scenario"]
    assert "rubric" not in scenario
    assert "qaSubmissions" not in scenario
    for option in scenario["decisionOptions"]:
        assert "consequence" not in option
        assert "rubricNote" not in option
        assert "decisionPoints" not in option


def test_submit_requires_evidence_and_valid_rationale(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    option_id = challenge["scenario"]["decisionOptions"][0]["id"]

    no_evidence = client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={"selectedOptionId": option_id, "rationale": VALID_RATIONALE},
    )
    assert no_evidence.status_code == 422
    assert no_evidence.json()["detail"]["code"] == "no_evidence_reviewed"

    _review_all_evidence(client, headers, challenge)

    too_short = client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={"selectedOptionId": option_id, "rationale": "nope"},
    )
    assert too_short.status_code == 422

    unknown_option = client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={"selectedOptionId": "does-not-exist", "rationale": VALID_RATIONALE},
    )
    assert unknown_option.status_code == 400


def test_evidence_interactions_are_idempotent(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    card_id = challenge["scenario"]["evidenceCards"][0]["id"]
    first = client.post(
        f"/v1/attempts/{attempt_id}/evidence",
        headers=headers,
        json={"evidenceCardId": card_id},
    ).json()
    second = client.post(
        f"/v1/attempts/{attempt_id}/evidence",
        headers=headers,
        json={"evidenceCardId": card_id},
    ).json()
    assert first["reviewedCount"] == second["reviewedCount"] == 1


def test_draft_is_saved_and_becomes_immutable_after_submit(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    _review_all_evidence(client, headers, challenge)

    saved = client.put(
        f"/v1/attempts/{attempt_id}/draft",
        headers=headers,
        json={"rationale": "half an idea"},
    )
    assert saved.status_code == 200
    assert saved.json()["rationaleLength"] == len("half an idea")

    assert _submit(client, headers, challenge).status_code == 200

    blocked = client.put(
        f"/v1/attempts/{attempt_id}/draft",
        headers=headers,
        json={"rationale": "changed my mind"},
    )
    assert blocked.status_code == 409


def test_repeated_submit_awards_xp_once(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    _review_all_evidence(client, headers, challenge)

    key = str(uuid.uuid4())
    first = _submit(client, headers, challenge, key)
    second = _submit(client, headers, challenge, key)
    third = _submit(client, headers, challenge, str(uuid.uuid4()))
    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json()["consequence"]["text"] == second.json()["consequence"]["text"]

    assert drain() >= 1

    db = SessionLocal()
    try:
        entries = (
            db.query(XpLedgerEntry).filter(XpLedgerEntry.attempt_id == attempt_id).all()
        )
        reasons = [entry.reason for entry in entries]
        assert len(reasons) == len(set(reasons))
        assert "daily_completion" in reasons
        attempt = db.get(ChallengeAttempt, attempt_id)
        assert attempt.status == "complete"
        assignment = db.get(LearningPathAssignment, attempt.assignment_id)
        assert assignment.status == "evaluated"
    finally:
        db.close()


def test_feedback_lifecycle_and_score_bounds(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    _review_all_evidence(client, headers, challenge)

    before = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers)
    assert before.status_code == 409  # cannot reach feedback before submitting

    _submit(client, headers, challenge)
    pending = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    assert pending["status"] == "pending"
    assert pending["feedback"] is None
    assert len(pending["consequence"]["text"]) > 50  # authored, available immediately

    drain()

    done = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    assert done["status"] == "complete"
    body = done["feedback"]
    breakdown = body["breakdown"]
    assert body["score"] == (
        breakdown["evidence"]
        + breakdown["decision"]
        + breakdown["rationale"]
        + breakdown["communication"]
    )
    assert 0 <= body["score"] <= 100
    assert breakdown["evidence"] <= breakdown["evidenceMax"]
    assert breakdown["decision"] <= breakdown["decisionMax"]
    assert breakdown["rationale"] <= breakdown["rationaleMax"]
    assert breakdown["communication"] <= breakdown["communicationMax"]
    for impact in body["skillImpact"]:
        assert -3 <= impact["delta"] <= 8
        assert 0 <= impact["score"] <= 100


def test_a_defensible_alternative_is_not_failed_automatically(client):
    """Spec §21: a non-reference option defended with evidence must not auto-fail."""
    headers, _ = onboard(client)
    today = client.get("/v1/today", headers=headers).json()
    challenge = client.get(
        f"/v1/challenges/{today['assignment']['assignmentId']}", headers=headers
    ).json()
    _review_all_evidence(client, headers, challenge)

    options = challenge["scenario"]["decisionOptions"]
    attempt_id = challenge["attempt"]["attemptId"]
    response = client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "selectedOptionId": options[-1]["id"],
            "rationale": (
                "I am choosing the less obvious option deliberately. The evidence "
                "supports it: the segment data isolates the cause, and the trade-off "
                "I accept is slower delivery in exchange for a reversible change. I "
                "would measure weekly conversion and revisit if it does not move."
            ),
        },
    )
    assert response.status_code == 200
    drain()
    feedback = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    assert feedback["status"] == "complete"
    # Evidence + a well-argued alternative should clear a bare pass on its own.
    assert feedback["feedback"]["score"] >= 40


def test_ownership_is_enforced_from_the_token(client):
    headers_a, _ = onboard(client)
    challenge = start_challenge(client, headers_a)
    attempt_id = challenge["attempt"]["attemptId"]
    assignment_id = challenge["assignmentId"]

    other = client.post(
        "/v1/auth/dev", json={"deviceId": f"intruder-{uuid.uuid4()}"}
    ).json()
    headers_b = {"Authorization": f"Bearer {other['accessToken']}"}

    assert client.get(f"/v1/challenges/{assignment_id}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers_b).status_code == 404
    assert (
        client.put(
            f"/v1/attempts/{attempt_id}/draft", headers=headers_b, json={"rationale": "x"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/v1/attempts/{attempt_id}/evidence",
            headers=headers_b,
            json={"evidenceCardId": "funnel"},
        ).status_code
        == 404
    )


def test_progress_and_history_reflect_server_state(client):
    headers, _ = onboard(client)
    challenge = start_challenge(client, headers)
    _review_all_evidence(client, headers, challenge)
    _submit(client, headers, challenge)
    drain()

    progress = client.get("/v1/progress", headers=headers).json()
    assert progress["completedCount"] == 1
    assert progress["totalXp"] >= 50
    assert progress["streakCount"] == 1
    assert len(progress["activity"]) == 7
    assert len(progress["skills"]) == 6
    assert "not an assessment of job readiness" in progress["footnote"]

    history = client.get("/v1/history", headers=headers).json()
    assert len(history["items"]) == 1
    assert history["items"][0]["feedbackStatus"] == "complete"


def test_analytics_endpoint_drops_free_text(client):
    headers, _ = onboard(client)
    response = client.post(
        "/v1/events",
        headers=headers,
        json={
            "events": [
                {
                    "name": "attempt_submitted",
                    "properties": {
                        "scenarioId": "onboarding-retention-drop",
                        "evidenceCount": 4,
                        "rationale": "this should never be stored",
                    },
                }
            ]
        },
    )
    assert response.status_code == 200

    from app.models import AnalyticsEvent

    db = SessionLocal()
    try:
        event = (
            db.query(AnalyticsEvent)
            .filter(AnalyticsEvent.name == "attempt_submitted")
            .order_by(AnalyticsEvent.created_at.desc())
            .first()
        )
        assert event is not None
        assert "rationale" not in event.properties
        assert event.properties["evidenceCount"] == 4
    finally:
        db.close()


def test_account_deletion_removes_rationales(client):
    headers, me = onboard(client)
    challenge = start_challenge(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    _review_all_evidence(client, headers, challenge)
    _submit(client, headers, challenge)
    drain()

    assert client.delete("/v1/me", headers=headers).status_code == 200
    assert client.get("/v1/me", headers=headers).status_code == 401

    db = SessionLocal()
    try:
        attempt = db.get(ChallengeAttempt, attempt_id)
        assert attempt is not None
        assert attempt.rationale is None
    finally:
        db.close()
