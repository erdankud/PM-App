"""Score bounds, XP and level arithmetic (spec §12)."""

from __future__ import annotations

import pytest

from app.services.scoring import (
    COMMUNICATION_MAX,
    DECISION_MAX,
    EVIDENCE_MAX,
    RATIONALE_MAX,
    build_breakdown,
    clamp_skill_delta,
    decision_points,
    evidence_points,
    level_for_xp,
    score_band,
    xp_for_next_level,
    xp_for_score,
)


def test_component_budget_sums_to_100():
    assert EVIDENCE_MAX + DECISION_MAX + RATIONALE_MAX + COMMUNICATION_MAX == 100


@pytest.mark.parametrize(
    ("opened", "total", "expected"),
    [
        (0, 4, 0),
        (1, 4, 5),
        (2, 4, 8),
        (3, 4, 12),
        (4, 4, 15),
        (9, 4, 15),
        (1, 1, 15),
        (1, 0, 0),
    ],
)
def test_evidence_points_curve(opened, total, expected):
    assert evidence_points(opened, total) == expected


def test_evidence_points_never_exceed_cap():
    for total in range(1, 5):
        for opened in range(0, 10):
            assert 0 <= evidence_points(opened, total) <= EVIDENCE_MAX


def test_decision_points_from_authored_weight():
    scenario = {
        "decisionOptions": [
            {"id": "a", "decisionPoints": 25},
            {"id": "b", "decisionPoints": 12},
        ]
    }
    assert decision_points(scenario, "a") == 25
    assert decision_points(scenario, "b") == 12
    with pytest.raises(KeyError):
        decision_points(scenario, "missing")


def test_breakdown_clamps_out_of_range_model_output():
    breakdown = build_breakdown(evidence=99, decision=99, rationale=999, communication=-5)
    assert breakdown.evidence == EVIDENCE_MAX
    assert breakdown.decision == DECISION_MAX
    assert breakdown.rationale == RATIONALE_MAX
    assert breakdown.communication == 0
    assert breakdown.total <= 100


def test_skill_delta_bounds():
    assert clamp_skill_delta(50) == 8
    assert clamp_skill_delta(-50) == -3
    assert clamp_skill_delta(0) == 0
    assert clamp_skill_delta(4.6) == 5


@pytest.mark.parametrize(
    ("score", "base", "bonus"),
    [(0, 50, 0), (50, 50, 0), (75, 50, 25), (100, 50, 50)],
)
def test_xp_for_score(score, base, bonus):
    assert xp_for_score(score) == (base, bonus)


def test_xp_bonus_never_exceeds_cap():
    for score in range(0, 101):
        base, bonus = xp_for_score(score)
        assert base == 50
        assert 0 <= bonus <= 50


@pytest.mark.parametrize(
    # Recalibrated in v0.2 for ~140 lessons and 18 gates rather than a daily challenge.
    ("xp", "level"),
    [(0, 1), (149, 1), (150, 2), (399, 2), (400, 3), (799, 3), (800, 4),
     (1400, 5), (2200, 6), (3000, 7)],
)
def test_level_thresholds(xp, level):
    assert level_for_xp(xp) == level


def test_level_is_monotonic():
    previous = 0
    for xp in range(0, 5000, 25):
        level = level_for_xp(xp)
        assert level >= previous
        previous = level


def test_next_level_target_is_always_ahead():
    for xp in (0, 199, 200, 899, 900, 1500, 4321):
        target = xp_for_next_level(xp)
        assert target is not None and target > xp


@pytest.mark.parametrize(
    ("score", "expected"),
    [(95, "Strong reasoning"), (72, "Solid reasoning"), (60, "Developing reasoning"),
     (45, "Early reasoning"), (10, "Needs a fuller argument")],
)
def test_score_band(score, expected):
    assert score_band(score) == expected
