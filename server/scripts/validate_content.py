#!/usr/bin/env python3
"""Validate authored content against the schema and the editorial rules.

    python -m scripts.validate_content

Exits non-zero if anything fails, so it can gate a build.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.content import (  # noqa: E402
    ContentError,
    assessment_content,
    load_scenario_file,
    scenario_paths,
    validate_scenario,
)

MIN_PUBLISHED = 12  # spec §21 quality acceptance


def main() -> int:
    paths = scenario_paths()
    if not paths:
        print("No scenario files found.")
        return 1

    failures = 0
    published = 0
    levels: Counter[str] = Counter()
    primary_skills: Counter[str] = Counter()

    for path in paths:
        try:
            data = load_scenario_file(path)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {path.name}: could not parse JSON ({exc})")
            failures += 1
            continue
        errors = validate_scenario(data)
        if errors:
            failures += 1
            print(f"FAIL {path.name}")
            for error in errors:
                print(f"     - {error}")
            continue
        if data["status"] == "published":
            published += 1
            levels[data["level"]] += 1
            primary_skills[data["primarySkill"]] += 1
        print(f"ok   {path.name}  [{data['level']}/{data['primarySkill']}]")

    try:
        assessment = assessment_content()
        print(f"ok   assessment.json  [{len(assessment['items'])} items]")
    except ContentError as exc:
        print(f"FAIL assessment.json: {exc}")
        failures += 1

    print()
    print(f"Published scenarios: {published}")
    print(f"  by level:  {dict(levels)}")
    print(f"  by skill:  {dict(primary_skills)}")

    if published < MIN_PUBLISHED:
        print(f"FAIL fewer than {MIN_PUBLISHED} published scenarios (spec §21)")
        failures += 1

    missing_levels = {"foundation", "developing", "advanced"} - set(levels)
    if missing_levels:
        print(f"FAIL no published scenarios at level(s): {sorted(missing_levels)}")
        failures += 1

    if failures:
        print(f"\n{failures} problem(s) found.")
        return 1
    print("\nAll content valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
