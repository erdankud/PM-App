"""Analytics sink (spec §19).

Event metadata only. Free-text rationale, AI feedback copy, Apple identity tokens
and email must never reach this endpoint; anything that looks like free text is
dropped server-side as a second line of defence.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.models import AnalyticsEvent
from app.schemas import AnalyticsBatch, SimpleOk

router = APIRouter(tags=["analytics"])

MAX_PROPERTY_CHARS = 120
BLOCKED_PROPERTY_KEYS = {
    "rationale",
    "rationale_text",
    "feedback",
    "feedback_text",
    "sharper_approach",
    "identity_token",
    "email",
    "access_token",
    "refresh_token",
}


def _sanitise(properties: dict) -> dict:
    clean: dict = {}
    for key, value in list(properties.items())[:20]:
        if key.lower() in BLOCKED_PROPERTY_KEYS:
            continue
        if isinstance(value, str):
            if len(value) > MAX_PROPERTY_CHARS:
                continue
            clean[key] = value
        elif isinstance(value, (int, float, bool)) or value is None:
            clean[key] = value
    return clean


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.post("/events", response_model=SimpleOk)
def ingest_events(payload: AnalyticsBatch, user: CurrentUser, db: DbSession) -> SimpleOk:
    for event in payload.events:
        db.add(
            AnalyticsEvent(
                user_id=user.id,
                name=event.name,
                properties=_sanitise(event.properties),
                app_version=event.app_version,
                platform=event.platform,
                client_timestamp=_parse_ts(event.client_timestamp),
            )
        )
    db.commit()
    return SimpleOk()
