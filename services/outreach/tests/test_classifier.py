"""Heuristic + LLM-fallback response classifier tests."""

from __future__ import annotations

import pytest

from outreach_svc.classifier import classify, classify_heuristic
from wfi_llm import NullModelRouter


def test_interested_keywords():
    out = classify_heuristic("Yes, send more info")
    assert out.label == "interested"


def test_not_interested_keywords():
    out = classify_heuristic("Please remove me from your list. Not interested.")
    assert out.label == "not_interested"


def test_timing_keywords():
    out = classify_heuristic("Reach out next quarter, not right now")
    assert out.label == "timing_not_right"


def test_counteroffer_signal():
    out = classify_heuristic("My current company is making a counteroffer that matches the new offer")
    assert out.label == "counteroffer_signal"


def test_ooo():
    out = classify_heuristic("I am out of the office until next Monday")
    assert out.label == "ooo"


def test_reroute():
    out = classify_heuristic("I'd talk to Sarah on my team — she's a better fit for this")
    assert out.label == "wrong_fit_route"


def test_unknown_returns_unknown():
    out = classify_heuristic("hmm")
    assert out.label == "unknown"


def test_empty_returns_unknown():
    out = classify_heuristic("")
    assert out.label == "unknown"


@pytest.mark.asyncio
async def test_llm_fallback_runs_when_heuristic_unknown():
    router = NullModelRouter(
        response_text='{"label": "interested", "confidence": 0.7, "reasoning": "tone"}',
    )
    out = await classify("hmm let me think about this", router=router)
    assert out.label == "interested"
    assert out.method == "llm"


@pytest.mark.asyncio
async def test_llm_not_called_when_heuristic_classifies():
    router = NullModelRouter(response_text='{"label": "interested", "confidence": 0.9}')
    out = await classify("Not interested, please remove", router=router)
    assert out.label == "not_interested"
    assert out.method == "heuristic"
    assert router.calls == []
