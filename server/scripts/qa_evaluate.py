#!/usr/bin/env python3
"""Evaluation test harness (spec §11, §22).

Runs every scenario's authored QA fixtures through the currently configured
evaluator and reports the resulting total score against the expected band. Use this
before publishing content, and again whenever the provider or prompt changes.

    EVALUATOR_PROVIDER=gemini EVALUATOR_API_KEY=... python -m scripts.qa_evaluate
    python -m scripts.qa_evaluate --scenario onboarding-retention-drop

A defensible alternative that scores like a weak answer is a content bug, not a
model bug: it usually means the option weights or the rubric need work.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.base import EvaluationRequest, ProviderError  # noqa: E402
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from app.ai.registry import get_provider  # noqa: E402
from app.ai.validation import InvalidEvaluation, parse_evaluation  # noqa: E402
from app.config import settings  # noqa: E402
from app.content import load_all_scenarios  # noqa: E402
from app.services.scoring import build_breakdown, evidence_points  # noqa: E402


def run_fixture(scenario: dict, qa: dict) -> tuple[int, dict]:
    option = next(
        o for o in scenario["decisionOptions"] if o["id"] == qa["optionId"]
    )
    request = EvaluationRequest(
        scenario_id=scenario["id"],
        scenario_version=scenario["version"],
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt(
            scenario=scenario,
            selected_option_id=qa["optionId"],
            reviewed_evidence_ids=qa["evidenceIds"],
            rationale=qa["rationale"],
        ),
        context={
            "rationale": qa["rationale"],
            "reviewed_evidence_ids": qa["evidenceIds"],
            "total_evidence_cards": len(scenario["evidenceCards"]),
            "decision_points": option["decisionPoints"],
            "primary_skill": scenario["primarySkill"],
            "secondary_skills": scenario.get("secondarySkills", []),
        },
    )
    provider = get_provider()
    response = provider.evaluate(request)
    result = parse_evaluation(response.raw_text)
    breakdown = build_breakdown(
        evidence=evidence_points(
            len(qa["evidenceIds"]), len(scenario["evidenceCards"])
        ),
        decision=option["decisionPoints"],
        rationale=result.rationale_score,
        communication=result.communication_score,
    )
    return breakdown.total, {
        "evidence": breakdown.evidence,
        "decision": breakdown.decision,
        "rationale": breakdown.rationale,
        "communication": breakdown.communication,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="run a single scenario id")
    args = parser.parse_args()

    scenarios = load_all_scenarios()
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
        if not scenarios:
            print(f"No scenario with id '{args.scenario}'")
            return 1

    print(f"Provider: {settings.evaluator_provider}")
    if settings.evaluator_provider == "mock":
        print(
            "WARNING: the mock evaluator is a deterministic development stub. "
            "Results here say nothing about real feedback quality.\n"
        )

    misses = 0
    ordering_problems = 0
    for scenario in scenarios:
        print(f"\n{scenario['id']}  ({scenario['level']}/{scenario['primarySkill']})")
        scores: dict[str, int] = {}
        for qa in scenario["qaSubmissions"]:
            try:
                total, parts = run_fixture(scenario, qa)
            except (ProviderError, InvalidEvaluation) as exc:
                print(f"  {qa['label']:<24} ERROR {exc}")
                misses += 1
                continue
            scores[qa["label"]] = total
            low, high = qa["expectedScoreMin"], qa["expectedScoreMax"]
            inside = low <= total <= high
            flag = "ok " if inside else "OUT"
            if not inside:
                misses += 1
            print(
                f"  {qa['label']:<24} {total:>3}  expected {low}-{high}  {flag}  "
                f"(e{parts['evidence']} d{parts['decision']} "
                f"r{parts['rationale']} c{parts['communication']})"
            )
        strong = scores.get("strong")
        weak = scores.get("weak")
        alt = scores.get("defensible_alternative")
        if strong is not None and weak is not None and strong <= weak:
            print("  ORDERING strong should outscore weak")
            ordering_problems += 1
        if alt is not None and weak is not None and alt <= weak:
            print("  ORDERING defensible alternative should outscore weak")
            ordering_problems += 1

    print()
    print(f"Fixtures outside their expected band: {misses}")
    print(f"Ordering problems: {ordering_problems}")
    return 1 if ordering_problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
