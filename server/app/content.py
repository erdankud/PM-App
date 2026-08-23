"""Authored content loading and validation.

Scenario JSON is the editorial source of truth; it is validated against
content/scenario.schema.json before it can be seeded (spec §11, §22).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from app.config import settings


class ContentError(RuntimeError):
    pass


@lru_cache
def scenario_schema() -> dict[str, Any]:
    path = settings.content_dir / "scenario.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def assessment_content() -> dict[str, Any]:
    path = settings.content_dir / "assessment.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_assessment(data)
    return data


def scenario_paths() -> list[Path]:
    return sorted((settings.content_dir / "scenarios").glob("*.json"))


def load_scenario_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_scenario(scenario: dict[str, Any]) -> list[str]:
    """Schema plus editorial rules that JSON Schema cannot express."""
    validator = Draft7Validator(scenario_schema())
    errors = [
        f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(scenario)
    ]
    if errors:
        return errors

    option_ids = [o["id"] for o in scenario["decisionOptions"]]
    evidence_ids = [c["id"] for c in scenario["evidenceCards"]]

    if len(set(option_ids)) != len(option_ids):
        errors.append("decisionOptions: duplicate option id")
    if len(set(evidence_ids)) != len(evidence_ids):
        errors.append("evidenceCards: duplicate evidence card id")

    orders = sorted(c["order"] for c in scenario["evidenceCards"])
    if orders != list(range(1, len(orders) + 1)):
        errors.append("evidenceCards: order must be 1..n with no gaps")

    if scenario["primarySkill"] in scenario["secondarySkills"]:
        errors.append("secondarySkills: must not repeat primarySkill")

    points = [o["decisionPoints"] for o in scenario["decisionOptions"]]
    if max(points) < 20:
        errors.append(
            "decisionOptions: at least one option must be a strong choice "
            "(decisionPoints >= 20)"
        )
    # Spec §11: at least one non-reference answer must earn meaningful partial credit.
    non_reference = sorted(points, reverse=True)[1:]
    if not non_reference or max(non_reference) < 8:
        errors.append(
            "decisionOptions: at least one non-reference option must earn meaningful "
            "partial credit (decisionPoints >= 8)"
        )

    labels = {q["label"] for q in scenario["qaSubmissions"]}
    for required in ("strong", "weak", "defensible_alternative"):
        if required not in labels:
            errors.append(f"qaSubmissions: missing a '{required}' fixture")

    for qa in scenario["qaSubmissions"]:
        if qa["optionId"] not in option_ids:
            errors.append(f"qaSubmissions: unknown optionId '{qa['optionId']}'")
        for eid in qa["evidenceIds"]:
            if eid not in evidence_ids:
                errors.append(f"qaSubmissions: unknown evidenceId '{eid}'")
        if qa["expectedScoreMin"] > qa["expectedScoreMax"]:
            errors.append("qaSubmissions: expectedScoreMin exceeds expectedScoreMax")

    return errors


def validate_assessment(data: dict[str, Any]) -> None:
    from app.models import SKILL_KEYS

    items = data.get("items", [])
    if len(items) != 3:
        raise ContentError("assessment.json must contain exactly 3 diagnostic items")
    seen_ids: set[str] = set()
    for item in items:
        if item["id"] in seen_ids:
            raise ContentError(f"assessment.json: duplicate item id {item['id']}")
        seen_ids.add(item["id"])
        options = item["options"]
        if not 2 <= len(options) <= 4:
            raise ContentError(f"assessment item {item['id']}: needs 2-4 options")
        for option in options:
            weights = option["skillWeights"]
            missing = set(SKILL_KEYS) - set(weights)
            if missing:
                raise ContentError(
                    f"assessment item {item['id']} option {option['id']}: "
                    f"missing skill weights {sorted(missing)}"
                )
            for key, value in weights.items():
                if key not in SKILL_KEYS:
                    raise ContentError(f"unknown skill key '{key}'")
                if not -15 <= value <= 15:
                    raise ContentError(f"skill weight out of range for '{key}'")


def load_all_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[tuple[str, int]] = set()
    for path in scenario_paths():
        data = load_scenario_file(path)
        errors = validate_scenario(data)
        if errors:
            problems.extend(f"{path.name}: {e}" for e in errors)
            continue
        key = (data["id"], data["version"])
        if key in seen:
            problems.append(f"{path.name}: duplicate scenario id/version {key}")
            continue
        seen.add(key)
        scenarios.append(data)
    if problems:
        raise ContentError("Invalid scenario content:\n  " + "\n  ".join(problems))
    return scenarios
