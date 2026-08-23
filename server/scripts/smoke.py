#!/usr/bin/env python3
"""End-to-end smoke test against a running server.

    python -m scripts.smoke [base_url]

Walks the whole P0 journey: dev sign-in, goal, assessment, path, today, challenge,
evidence, draft, duplicate submit, feedback polling, rating, progress, history.
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
API = f"{BASE}/v1"

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    status = "ok  " if condition else "FAIL"
    print(f"{status} {message}")
    if not condition:
        failures.append(message)


def main() -> int:
    client = httpx.Client(timeout=30.0)

    health = client.get(f"{BASE}/health").json()
    check(health.get("status") == "ok", "health endpoint responds")

    device_id = f"smoke-{uuid.uuid4()}"
    auth = client.post(
        f"{API}/auth/dev", json={"deviceId": device_id, "timezone": "Europe/London"}
    )
    check(auth.status_code == 200, f"dev sign-in ({auth.status_code})")
    tokens = auth.json()
    headers = {"Authorization": f"Bearer {tokens['accessToken']}"}
    check(tokens["user"]["onboardingStatus"] == "signed_in", "new user starts at signed_in")

    unauth = client.get(f"{API}/me")
    check(unauth.status_code == 401, "unauthenticated /me is rejected")

    profile = client.patch(
        f"{API}/me/profile", headers=headers, json={"goal": "break_into_pm"}
    )
    check(profile.status_code == 200, "goal selection persists")
    check(profile.json()["goal"] == "break_into_pm", "goal round-trips")

    result = None
    for _ in range(5):
        state = client.get(f"{API}/assessment", headers=headers).json()
        if state["completed"]:
            break
        item = state["nextItem"]
        answer = client.post(
            f"{API}/assessment/responses",
            headers=headers,
            json={"itemId": item["id"], "choiceId": item["options"][0]["id"]},
        )
        check(answer.status_code == 200, f"assessment item {item['index']} accepted")
        result = answer.json().get("result")
    check(result is not None, "assessment produced a path")
    if result:
        check(len(result["path"]) == 7, f"path has 7 days (got {len(result['path'])})")
        check(len(result["focusSkills"]) == 2, "two focus skills identified")
        check(
            result["startingLevel"] in {"foundation", "developing", "advanced"},
            "starting level is a valid band",
        )

    complete = client.patch(
        f"{API}/me/profile", headers=headers, json={"completeOnboarding": True}
    )
    check(complete.status_code == 200, "onboarding completes")

    today = client.get(f"{API}/today", headers=headers)
    check(today.status_code == 200, f"today resolves ({today.status_code})")
    assignment = today.json()["assignment"]
    check(assignment["state"] == "not_started", "today starts as not_started")

    challenge = client.get(
        f"{API}/challenges/{assignment['assignmentId']}", headers=headers
    ).json()
    attempt_id = challenge["attempt"]["attemptId"]
    scenario = challenge["scenario"]
    check(2 <= len(scenario["evidenceCards"]) <= 4, "scenario has 2-4 evidence cards")
    check(
        all("consequence" not in o for o in scenario["decisionOptions"]),
        "consequence text is withheld before submit",
    )
    check("rubric" not in scenario, "rubric is never sent to the client")

    early = client.post(
        f"{API}/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "selectedOptionId": scenario["decisionOptions"][0]["id"],
            "rationale": "x" * 40,
        },
    )
    check(early.status_code == 422, "submit blocked with no evidence reviewed")

    evidence = client.post(
        f"{API}/attempts/{attempt_id}/evidence",
        headers=headers,
        json={"evidenceCardId": scenario["evidenceCards"][0]["id"]},
    ).json()
    repeat = client.post(
        f"{API}/attempts/{attempt_id}/evidence",
        headers=headers,
        json={"evidenceCardId": scenario["evidenceCards"][0]["id"]},
    ).json()
    check(repeat["reviewedCount"] == evidence["reviewedCount"] == 1, "evidence open is idempotent")

    for card in scenario["evidenceCards"][1:]:
        client.post(
            f"{API}/attempts/{attempt_id}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )

    option_id = scenario["decisionOptions"][0]["id"]
    draft = client.put(
        f"{API}/attempts/{attempt_id}/draft",
        headers=headers,
        json={"selectedOptionId": option_id, "rationale": "partial thought"},
    )
    check(draft.status_code == 200, "draft autosaves")

    resumed = client.get(
        f"{API}/challenges/{assignment['assignmentId']}", headers=headers
    ).json()
    check(resumed["attempt"]["rationale"] == "partial thought", "draft survives a reload")
    check(resumed["state"] == "in_progress", "state reflects an in-progress draft")

    short = client.post(
        f"{API}/attempts/{attempt_id}/submit",
        headers=headers,
        json={"selectedOptionId": option_id, "rationale": "too short"},
    )
    check(short.status_code == 422, "rationale under 30 characters is rejected")

    rationale = (
        "I would take this option because the funnel evidence points at one step "
        "rather than the whole flow, and the cheaper fix is reversible. The trade-off "
        "is that I am acting on a hypothesis; I would measure the step conversion "
        "weekly and revisit if it does not move."
    )
    key = str(uuid.uuid4())
    submit = client.post(
        f"{API}/attempts/{attempt_id}/submit",
        headers=headers | {"Idempotency-Key": key},
        json={"selectedOptionId": option_id, "rationale": rationale},
    )
    check(submit.status_code == 200, f"submit accepted ({submit.status_code})")
    body = submit.json()
    check(len(body["consequence"]["text"]) > 50, "authored consequence returned immediately")

    duplicate = client.post(
        f"{API}/attempts/{attempt_id}/submit",
        headers=headers | {"Idempotency-Key": key},
        json={"selectedOptionId": option_id, "rationale": rationale},
    )
    check(duplicate.status_code == 200, "duplicate submit does not error")
    check(
        duplicate.json()["consequence"]["text"] == body["consequence"]["text"],
        "duplicate submit returns the same result",
    )

    feedback = None
    for _ in range(30):
        feedback = client.get(f"{API}/attempts/{attempt_id}/feedback", headers=headers).json()
        if feedback["status"] in {"complete", "failed"}:
            break
        time.sleep(1)
    check(feedback and feedback["status"] == "complete", f"feedback completes ({feedback['status'] if feedback else 'none'})")

    if feedback and feedback["status"] == "complete":
        detail = feedback["feedback"]
        breakdown = detail["breakdown"]
        computed = (
            breakdown["evidence"]
            + breakdown["decision"]
            + breakdown["rationale"]
            + breakdown["communication"]
        )
        check(detail["score"] == computed, "score equals the sum of its components")
        check(0 <= detail["score"] <= 100, "score is inside 0-100")
        check(detail["xpAwarded"] >= 50, "base XP awarded")
        check(
            all(-3 <= s["delta"] <= 8 for s in detail["skillImpact"]),
            "skill deltas are inside -3..8",
        )
        check(bool(detail["sharperApproach"]), "sharper approach present")

    rating = client.post(
        f"{API}/attempts/{attempt_id}/feedback-rating",
        headers=headers,
        json={"rating": "useful"},
    )
    check(rating.status_code == 200, "feedback rating stored")

    progress = client.get(f"{API}/progress", headers=headers).json()
    check(progress["completedCount"] == 1, "progress counts the completed challenge")
    check(len(progress["skills"]) == 6, "six skills reported")
    check(len(progress["activity"]) == 7, "seven-day activity strip")
    check(progress["totalXp"] >= 50, "XP reflected in profile")

    history = client.get(f"{API}/history", headers=headers).json()
    check(len(history["items"]) == 1, "history lists the attempt")

    after = client.get(f"{API}/today", headers=headers).json()
    check(after["assignment"]["state"] == "complete", "today reflects completion")

    other = client.post(
        f"{API}/auth/dev", json={"deviceId": f"smoke-other-{uuid.uuid4()}"}
    ).json()
    other_headers = {"Authorization": f"Bearer {other['accessToken']}"}
    stolen = client.get(f"{API}/attempts/{attempt_id}/feedback", headers=other_headers)
    check(stolen.status_code == 404, "another user cannot read this attempt")
    stolen_challenge = client.get(
        f"{API}/challenges/{assignment['assignmentId']}", headers=other_headers
    )
    check(stolen_challenge.status_code == 404, "another user cannot read this assignment")

    deleted = client.delete(f"{API}/me", headers=headers)
    check(deleted.status_code == 200, "account deletion succeeds")
    after_delete = client.get(f"{API}/me", headers=headers)
    check(after_delete.status_code == 401, "deleted account cannot be used")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
