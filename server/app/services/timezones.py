"""Timezone resolution.

Kept even though the daily path is gone: the timezone is still stored on the account
and still has to be validated before it reaches the database.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "UTC"


def resolve_timezone(name: str | None) -> ZoneInfo:
    """Never raises: an unknown or missing zone falls back to UTC."""
    if not name:
        return ZoneInfo(DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ZoneInfo(DEFAULT_TIMEZONE)
