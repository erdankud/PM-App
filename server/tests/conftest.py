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

from app import tree_content  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    # Tree, lessons and gate scenarios live in validated files, so there is nothing
    # to seed: creating the schema is the whole setup.
    Base.metadata.create_all(bind=engine)
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


def onboard(client: TestClient, language: str | None = None) -> tuple[dict, dict]:
    """Sign in and finish onboarding. There is no diagnostic any more (spec v0.2 §10).

    A fresh profile reads in English. Pass ``language="ru"`` to get the authored
    corpus: a test that needs Russian has to ask for it, rather than leaning on
    whatever the column default happens to be this month — that is how six tests
    came to depend on a default none of them were about.
    """
    auth = client.post(
        "/v1/auth/dev",
        json={"deviceId": f"test-{uuid.uuid4()}", "timezone": "Europe/Moscow"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['accessToken']}"}
    profile: dict = {"completeOnboarding": True}
    if language is not None:
        profile["language"] = language
    me = client.patch("/v1/me/profile", headers=headers, json=profile).json()
    return headers, me


def block_lessons(block_id: str) -> list[str]:
    return [lesson["id"] for lesson in tree_content.lessons_for_block(block_id)]


def read_all_lessons(client: TestClient, headers: dict, block_id: str) -> None:
    for lesson_id in block_lessons(block_id):
        client.post(f"/v1/lessons/{lesson_id}/complete", headers=headers)


def start_gate(client: TestClient, headers: dict, gate_id: str = "gate-d1") -> dict:
    response = client.post(f"/v1/gates/{gate_id}/start", headers=headers)
    assert response.status_code == 200, response.json()
    return response.json()
