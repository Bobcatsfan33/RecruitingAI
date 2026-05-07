"""Client SDK for the rules service.

Calls into `services/rules` (which wraps OPA) so every other service
shares a single API surface for "ask the rules engine X." Returns typed
results so the screening / pipeline / bench agents don't all reimplement
the same response parsing.
"""

from wfi_rules_sdk.client import RulesClient, RuleEvaluation
from wfi_rules_sdk.mock import MockRulesClient

__all__ = ["RulesClient", "RuleEvaluation", "MockRulesClient"]
