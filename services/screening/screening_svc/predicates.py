"""Deterministic predicate evaluator for employer-defined rubric criteria.

Predicate grammar (subset; LLM predicates are evaluated separately):

  field_eq:<jsonpath>=<literal>
  field_neq:<jsonpath>=<literal>
  field_in:<jsonpath> in [a, b, c]
  field_gte:<jsonpath>>=<number>
  field_lte:<jsonpath><=<number>
  field_present:<jsonpath>
  field_truthy:<jsonpath>
  llm:<prompt-key>             — handled by the screening agent, not here

`<jsonpath>` is a dotted path through the candidate dict — e.g.
``primary_motion`` or ``career_history.0.company``.
"""

from __future__ import annotations

import re
from typing import Any


def _follow(obj: Any, path: str) -> Any:
    cursor: Any = obj
    for part in path.split("."):
        if cursor is None:
            return None
        if isinstance(cursor, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            cursor = cursor[idx] if 0 <= idx < len(cursor) else None
        elif isinstance(cursor, dict):
            cursor = cursor.get(part)
        else:
            cursor = getattr(cursor, part, None)
    return cursor


def _coerce(value: str) -> Any:
    stripped = value.strip()
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    if stripped.lower() in {"null", "none"}:
        return None
    try:
        if "." in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped.strip("\"'")


_LIST_RE = re.compile(r"\s+in\s+\[(.+)\]")


def evaluate(predicate: str, candidate: dict[str, Any]) -> bool | None:
    """Return True/False, or None for predicates we cannot evaluate
    deterministically (e.g. ``llm:`` — the screening agent handles those).
    """
    if not predicate or ":" not in predicate:
        return None
    kind, _, body = predicate.partition(":")
    kind = kind.strip()
    body = body.strip()

    if kind == "llm":
        return None

    if kind == "field_present":
        return _follow(candidate, body) is not None

    if kind == "field_truthy":
        return bool(_follow(candidate, body))

    if kind == "field_eq":
        path, _, expected = body.partition("=")
        actual = _follow(candidate, path.strip())
        return actual == _coerce(expected)

    if kind == "field_neq":
        path, _, expected = body.partition("=")
        actual = _follow(candidate, path.strip())
        return actual != _coerce(expected)

    if kind == "field_in":
        match = _LIST_RE.search(body)
        if not match:
            return None
        path = body[: match.start()].strip()
        members = [_coerce(x) for x in match.group(1).split(",")]
        actual = _follow(candidate, path)
        if isinstance(actual, list):
            return any(item in members for item in actual)
        return actual in members

    if kind == "field_gte":
        path, _, threshold = body.partition(">=")
        actual = _follow(candidate, path.strip())
        if actual is None:
            return False
        try:
            return float(actual) >= float(threshold)
        except (TypeError, ValueError):
            return False

    if kind == "field_lte":
        path, _, threshold = body.partition("<=")
        actual = _follow(candidate, path.strip())
        if actual is None:
            return False
        try:
            return float(actual) <= float(threshold)
        except (TypeError, ValueError):
            return False

    return None
