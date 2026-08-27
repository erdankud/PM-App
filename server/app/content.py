"""Editorial rules for authored scenarios.

The v0.2 tree loads its content through `tree_content`; what lives here is the
editorial validation applied on top of the schema. The v0.1 scenario library that
used to sit beside it has been rewritten into blocks and removed.
"""

from __future__ import annotations

from typing import Any


class ContentError(RuntimeError):
    pass


def validate_scenario_rules(scenario: dict[str, Any]) -> list[str]:
    """Rules the JSON Schema cannot express.

    Schema and translation checks are deliberately not here: gate scenarios are
    authored in the content language rather than translated into it (spec v0.2 §16).
    """
    errors: list[str] = []
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


# Every language the app offers a switch for. A published scenario must be complete in
# all of them: a half-translated scenario would drop the reader into the other language
# mid-brief, which is worse than not offering the language at all.
