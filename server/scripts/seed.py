#!/usr/bin/env python3
"""Create tables (dev) and seed validated scenario content.

    python -m scripts.seed

Published content is immutable per (id, version): re-running only inserts versions
that do not exist yet, and refuses to alter an existing one (spec §14).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.content import load_all_scenarios  # noqa: E402
from app.db import engine, session_scope  # noqa: E402
from app.models import Base, Scenario  # noqa: E402


def main() -> int:
    Base.metadata.create_all(bind=engine)
    scenarios = load_all_scenarios()

    inserted = 0
    unchanged = 0
    with session_scope() as db:
        for data in scenarios:
            existing = (
                db.query(Scenario)
                .filter(
                    Scenario.scenario_id == data["id"],
                    Scenario.version == data["version"],
                )
                .first()
            )
            if existing is not None:
                unchanged += 1
                continue
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
            inserted += 1

    print(f"Seeded {inserted} scenario version(s); {unchanged} already present.")
    print(
        "Note: an edit to an already-seeded scenario needs a version bump so that "
        "historical attempts keep the content they were evaluated against."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
