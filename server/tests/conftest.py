from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_ROOT))

# Configure before anything imports app.config.
TEST_DB = SERVER_ROOT / f"test-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_DEV_AUTH"] = "true"
os.environ["EVALUATOR_PROVIDER"] = "mock"
os.environ["RUN_INLINE_WORKER"] = "false"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.content import load_all_scenarios  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Scenario  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for data in load_all_scenarios():
            db.add(
                Scenario(
                    scenario_id=data["id"],
                    version=data["version"],
                    status=data["status"],
                    title=data["title"],
                    summary=data["summary"],
                    estimated_minutes=data["estimatedMinutes"],
                    level=data["level"],
                    primary_skill=data["primarySkill"],
                    secondary_skills=data["secondarySkills"],
                    tags=data["tags"],
                    content=data,
                )
            )
        db.commit()
    finally:
        db.close()
    yield
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(str(TEST_DB) + suffix).unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def onboard(client: TestClient) -> tuple[dict, dict]:
    """Sign in, answer the assessment, complete onboarding. Returns (headers, me)."""
    auth = client.post(
        "/v1/auth/dev",
        json={"deviceId": f"test-{uuid.uuid4()}", "timezone": "Europe/London"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['accessToken']}"}
    client.patch("/v1/me/profile", headers=headers, json={"goal": "break_into_pm"})
    for _ in range(4):
        state = client.get("/v1/assessment", headers=headers).json()
        if state["completed"]:
            break
        item = state["nextItem"]
        client.post(
            "/v1/assessment/responses",
            headers=headers,
            json={"itemId": item["id"], "choiceId": item["options"][0]["id"]},
        )
    me = client.patch(
        "/v1/me/profile", headers=headers, json={"completeOnboarding": True}
    ).json()
    return headers, me


def start_challenge(client: TestClient, headers: dict) -> dict:
    today = client.get("/v1/today", headers=headers).json()
    assignment_id = today["assignment"]["assignmentId"]
    return client.get(f"/v1/challenges/{assignment_id}", headers=headers).json()
