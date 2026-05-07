"""A/B significance tests."""

from __future__ import annotations

from outreach_svc.ab import Arm, Experiment, evaluate, two_proportion_z


def test_no_data_returns_not_significant():
    sig = two_proportion_z(Arm("a"), Arm("b"))
    assert sig.significant is False


def test_clear_winner_detected():
    a = Arm("a", sent=400, responded=120)  # 30%
    b = Arm("b", sent=400, responded=40)   # 10%
    sig = two_proportion_z(a, b)
    assert sig.significant
    assert sig.winner == "a"


def test_no_difference_not_significant():
    a = Arm("a", sent=300, responded=60)
    b = Arm("b", sent=300, responded=63)
    sig = two_proportion_z(a, b)
    assert not sig.significant


def test_evaluate_requires_two_arms():
    exp = Experiment(key="x")
    exp.record("a", responded=True)
    assert evaluate(exp) is None


def test_evaluate_returns_significance_with_two_arms():
    exp = Experiment(key="subject_v1_vs_v2")
    for _ in range(200):
        exp.record("a", responded=True)
    for _ in range(200):
        exp.record("a", responded=False)
    for _ in range(50):
        exp.record("b", responded=True)
    for _ in range(350):
        exp.record("b", responded=False)
    sig = evaluate(exp)
    assert sig is not None
    assert sig.winner == "a"
    assert sig.significant
