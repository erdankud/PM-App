"""Model output is untrusted until validated (spec §13, §17)."""

from __future__ import annotations

import json

import pytest

from app.ai.validation import InvalidEvaluation, parse_evaluation

VALID = {
    "rationale_score": 30,
    "communication_score": 11,
    "strengths": [{"title": "Used the funnel", "detail": "You cited the step data."}],
    "improvements": [{"title": "Name the confound", "detail": "Say what the data cannot show."}],
    "sharper_approach": "Lead with the recommendation, then the strongest evidence.",
    "skill_deltas": {
        "discovery": 5,
        "value_design": 3,
        "delivery": 1,
        "marketing": 0,
        "growth": 0,
        "economics": 0,
        "communication": 2,
    },
    "needs_retry": False,
}


def test_parses_valid_payload():
    result = parse_evaluation(json.dumps(VALID))
    assert result.rationale_score == 30
    assert result.communication_score == 11
    assert result.skill_deltas["discovery"] == 5
    assert result.needs_retry is False


def test_parses_payload_wrapped_in_code_fence():
    text = "```json\n" + json.dumps(VALID) + "\n```"
    assert parse_evaluation(text).rationale_score == 30


def test_parses_payload_with_surrounding_prose():
    text = "Here is the evaluation:\n" + json.dumps(VALID) + "\nHope that helps."
    assert parse_evaluation(text).rationale_score == 30


def test_rejects_non_json():
    with pytest.raises(InvalidEvaluation):
        parse_evaluation("I cannot evaluate this submission.")


@pytest.mark.parametrize("value", [46, -1, 999])
def test_rejects_rationale_score_out_of_range(value):
    payload = dict(VALID, rationale_score=value)
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(payload))


@pytest.mark.parametrize("value", [16, -1])
def test_rejects_communication_score_out_of_range(value):
    payload = dict(VALID, communication_score=value)
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(payload))


@pytest.mark.parametrize("delta", [9, -4, 100])
def test_rejects_skill_delta_out_of_range(delta):
    deltas = dict(VALID["skill_deltas"], discovery=delta)
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(dict(VALID, skill_deltas=deltas)))


def test_rejects_unknown_skill_key():
    deltas = dict(VALID["skill_deltas"], leadership=3)
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(dict(VALID, skill_deltas=deltas)))


def test_missing_skill_key_defaults_to_zero():
    deltas = dict(VALID["skill_deltas"])
    del deltas["delivery"]
    result = parse_evaluation(json.dumps(dict(VALID, skill_deltas=deltas)))
    assert result.skill_deltas["delivery"] == 0


def test_truncates_overlong_text_rather_than_failing():
    payload = dict(VALID, sharper_approach="word " * 400)
    result = parse_evaluation(json.dumps(payload))
    assert len(result.sharper_approach) <= 700


def test_caps_number_of_coaching_items():
    payload = dict(
        VALID,
        strengths=[{"title": f"t{i}", "detail": f"detail number {i}"} for i in range(6)],
    )
    result = parse_evaluation(json.dumps(payload))
    assert len(result.strengths) == 2


def test_rejects_empty_coaching_when_not_flagged_for_retry():
    payload = dict(VALID, strengths=[], improvements=[])
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(payload))


def test_allows_empty_coaching_when_needs_retry():
    payload = dict(VALID, strengths=[], improvements=[], needs_retry=True)
    assert parse_evaluation(json.dumps(payload)).needs_retry is True


def test_rejects_non_boolean_needs_retry():
    with pytest.raises(InvalidEvaluation):
        parse_evaluation(json.dumps(dict(VALID, needs_retry="yes")))
