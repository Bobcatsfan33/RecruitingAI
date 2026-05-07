"""Human-escalation triggers.

Per blueprint Sprint 3:
- candidate is VP+ level
- comp exceeds $350K OTE
- candidate has active non-compete in same vertical
- mixed signals (some criteria pass, some critical fail)
"""

from __future__ import annotations

from typing import Any

from wfi_schemas import EscalationFlag

VP_PLUS_KEYWORDS = ("vp", "vice president", "chief", "head of", "president")
COMP_THRESHOLD = 350_000


def detect(
    candidate: dict[str, Any],
    *,
    ownership_status: dict[str, Any] | None = None,
    criterion_results: list[dict[str, Any]] | None = None,
) -> list[EscalationFlag]:
    flags: list[EscalationFlag] = []
    history = candidate.get("career_history") or []
    current = history[0] if history else {}
    title = (current.get("title") or "").lower()
    if any(keyword in title for keyword in VP_PLUS_KEYWORDS):
        flags.append(EscalationFlag.VP_PLUS)

    # Latest verified comp.
    comps = candidate.get("compensation_history") or []
    if comps:
        latest = comps[0]
        ote = latest.get("ote") or latest.get("base") or 0
        try:
            if float(ote) > COMP_THRESHOLD:
                flags.append(EscalationFlag.HIGH_COMP)
        except (TypeError, ValueError):
            pass

    if ownership_status:
        if ownership_status.get("has_non_compete"):
            flags.append(EscalationFlag.ACTIVE_NON_COMPETE)
        if ownership_status.get("has_exclusivity") or ownership_status.get("is_dnc"):
            flags.append(EscalationFlag.OWNERSHIP_BLOCKED)

    if criterion_results:
        passed = sum(1 for c in criterion_results if c.get("passed"))
        failed = sum(1 for c in criterion_results if c.get("passed") is False)
        # Mixed = neither overwhelmingly pass nor fail; both sides non-trivial.
        if passed >= 1 and failed >= 1 and abs(passed - failed) <= 1:
            flags.append(EscalationFlag.MIXED_SIGNALS)

    return flags
