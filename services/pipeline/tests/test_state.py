"""Pipeline state machine tests."""

from __future__ import annotations

from pipeline_svc.state import Stage, can_transition


def test_intake_to_sourcing_allowed():
    assert can_transition(Stage.INTAKE, Stage.SOURCING)


def test_screening_can_skip_to_submission():
    assert can_transition(Stage.SCREENING, Stage.SUBMISSION)


def test_offer_can_falloff():
    assert can_transition(Stage.OFFER, Stage.FALLOFF)


def test_falloff_can_re_enter_at_submission():
    assert can_transition(Stage.FALLOFF, Stage.SUBMISSION)


def test_placed_is_terminal():
    for target in Stage:
        assert not can_transition(Stage.PLACED, target)


def test_random_invalid_transition_rejected():
    assert not can_transition(Stage.OUTREACH, Stage.PLACED)
