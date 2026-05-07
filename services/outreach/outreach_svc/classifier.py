"""Response classifier.

Two-tier:
1. **Heuristic** — fast keyword + sentiment classifier. Handles ~80% of
   replies (clear "not interested", "send more info", out-of-office,
   counteroffer mention).
2. **LLM** — anything the heuristic returns ``unknown`` on goes to the
   light-tier model with a strict-JSON classification prompt.

Both paths return one of: ``interested``, ``timing_not_right``,
``not_interested``, ``wrong_fit_route``, ``counteroffer_signal``, ``ooo``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from wfi_llm import ModelRouter, ModelTier, NullModelRouter

ResponseClass = Literal[
    "interested",
    "timing_not_right",
    "not_interested",
    "wrong_fit_route",
    "counteroffer_signal",
    "ooo",
    "unknown",
]


@dataclass
class ClassificationResult:
    label: ResponseClass
    confidence: float
    method: str  # heuristic | llm
    reasoning: str = ""


_INTERESTED_RE = re.compile(
    r"\b(yes|interested|happy to chat|sure|let'?s talk|sounds good|"
    r"send (more|over)|share|tell me more|book|schedule|tomorrow|next week)\b",
    re.I,
)
_NOT_INTERESTED_RE = re.compile(
    r"\b(not interested|no thanks|no thank you|please remove|unsubscribe|"
    r"don'?t contact|stop emailing|happy where i am|love (my|where i)|"
    r"not looking|not (a )?fit)\b",
    re.I,
)
_TIMING_RE = re.compile(
    r"\b(not (right )?now|maybe later|circle back|reach out (in|next)|"
    r"after the (quarter|year|holidays)|once|when things settle)\b",
    re.I,
)
_OOO_RE = re.compile(
    r"\b(out of (the )?office|on (vacation|leave|holiday)|return(ing)?|away from email|"
    r"limited access)\b",
    re.I,
)
_REROUTE_RE = re.compile(
    r"\b(check (with|out)|talk to|speak (with|to)|forward(ed)? to|reach out to|"
    r"better fit (for|to))\s+\w+",
    re.I,
)
_COUNTEROFFER_RE = re.compile(
    r"\b(counter ?offer|matching|matched|countered|counter|raise|stayed back|"
    r"company is making (me|us) an offer)\b",
    re.I,
)


def classify_heuristic(reply_text: str) -> ClassificationResult:
    text = (reply_text or "").strip()
    if not text:
        return ClassificationResult(label="unknown", confidence=0.0, method="heuristic")

    if _OOO_RE.search(text):
        return ClassificationResult(label="ooo", confidence=0.9, method="heuristic")
    if _COUNTEROFFER_RE.search(text):
        return ClassificationResult(
            label="counteroffer_signal", confidence=0.85, method="heuristic",
            reasoning="counteroffer keyword match",
        )
    if _NOT_INTERESTED_RE.search(text):
        return ClassificationResult(
            label="not_interested", confidence=0.85, method="heuristic",
        )
    if _REROUTE_RE.search(text) and not _INTERESTED_RE.search(text):
        return ClassificationResult(
            label="wrong_fit_route", confidence=0.7, method="heuristic",
        )
    if _TIMING_RE.search(text):
        return ClassificationResult(
            label="timing_not_right", confidence=0.75, method="heuristic",
        )
    if _INTERESTED_RE.search(text):
        return ClassificationResult(
            label="interested", confidence=0.75, method="heuristic",
        )
    return ClassificationResult(label="unknown", confidence=0.0, method="heuristic")


_LLM_SYSTEM = """\
Classify the candidate's reply into exactly one of:
- interested
- timing_not_right
- not_interested
- wrong_fit_route
- counteroffer_signal
- ooo
- unknown

Return STRICT JSON: {"label": "<one of the above>", "confidence": 0..1, "reasoning": "<one sentence>"}.
"""


async def classify(
    reply_text: str,
    *,
    router: ModelRouter | NullModelRouter | None = None,
) -> ClassificationResult:
    heuristic = classify_heuristic(reply_text)
    if heuristic.label != "unknown" or router is None:
        return heuristic
    response = await router.acomplete(
        tier=ModelTier.LIGHT,
        system=_LLM_SYSTEM,
        user=reply_text,
        max_tokens=200,
        temperature=0.0,
    )
    try:
        data = json.loads(response.text)
        return ClassificationResult(
            label=data.get("label", "unknown"),
            confidence=float(data.get("confidence", 0.5)),
            method="llm",
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        return ClassificationResult(label="unknown", confidence=0.0, method="llm")
