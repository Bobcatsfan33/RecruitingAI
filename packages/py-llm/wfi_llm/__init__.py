"""Model router + Anthropic client wrapper.

Three tiers:
  - frontier (Claude Opus): high-stakes judgment (interview eval, exec screen)
  - mid     (Claude Sonnet): routine evaluation
  - lightweight (Claude Haiku): parsing, classification, formatting

Use ``MODEL_FOR_TASK`` to map a task name to a tier; the router picks the
matching configured model. Prompt caching is enabled by marking the system
prompt and any large reference blocks with ``cache_control``.
"""

from wfi_llm.router import (
    ModelRouter,
    ModelTier,
    NullModelRouter,
    RouterResponse,
)

__all__ = ["ModelRouter", "ModelTier", "NullModelRouter", "RouterResponse"]
