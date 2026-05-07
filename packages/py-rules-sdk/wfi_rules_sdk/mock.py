"""In-memory mock RulesClient for tests + dev when OPA isn't running."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from wfi_rules_sdk.client import RuleEvaluation


class MockRulesClient:
    """Register handlers for specific rule names; the rest return a stub."""

    def __init__(self):
        self.handlers: dict[str, Callable[[dict[str, Any]], RuleEvaluation]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def register(
        self,
        rule: str,
        handler: Callable[[dict[str, Any]], RuleEvaluation],
    ) -> None:
        self.handlers[rule] = handler

    async def aclose(self) -> None:
        return None

    async def evaluate(self, rule: str, inputs: dict[str, Any]) -> RuleEvaluation:
        self.calls.append((rule, inputs))
        if rule in self.handlers:
            return self.handlers[rule](inputs)
        return RuleEvaluation(rule=rule, verdict="allowed", reasoning="mock default")

    async def evaluate_many(
        self,
        rules: list[str],
        inputs: dict[str, Any],
    ) -> list[RuleEvaluation]:
        return [await self.evaluate(rule, inputs) for rule in rules]
