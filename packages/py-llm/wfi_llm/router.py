"""Anthropic model router with prompt caching."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import MessageParam, TextBlockParam
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = structlog.get_logger("wfi.llm")


class ModelTier(str, Enum):
    FRONTIER = "frontier"  # Opus — highest reasoning quality
    MID = "mid"            # Sonnet — balanced
    LIGHT = "light"        # Haiku — fast + cheap


# Default model identifiers — overridable via env so we can promote a
# new release without redeploys.
DEFAULT_MODELS: dict[ModelTier, str] = {
    ModelTier.FRONTIER: os.environ.get("WFI_MODEL_FRONTIER", "claude-opus-4-5"),
    ModelTier.MID:      os.environ.get("WFI_MODEL_MID",      "claude-sonnet-4-6"),
    ModelTier.LIGHT:    os.environ.get("WFI_MODEL_LIGHT",    "claude-haiku-4-5"),
}

# Approximate prices per 1M tokens (input / output). Used for cost telemetry,
# not billing. Update when Anthropic publishes new prices.
PRICE_TABLE: dict[str, tuple[float, float]] = {
    "claude-opus-4-5":   (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00, 5.00),
}


@dataclass
class RouterResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    raw: Any = field(default=None, repr=False)


class ModelRouter:
    """Wraps the Anthropic SDK with retries, caching, and cost telemetry."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        models: dict[ModelTier, str] | None = None,
        default_max_tokens: int = 2048,
    ) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for ModelRouter")
        self._client = Anthropic(api_key=key)
        self._aclient = AsyncAnthropic(api_key=key)
        self._models = models or DEFAULT_MODELS
        self._default_max_tokens = default_max_tokens

    def model_for(self, tier: ModelTier) -> str:
        return self._models[tier]

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    async def acomplete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        cached_blocks: list[str] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> RouterResponse:
        """Async completion. Marks ``system`` + every ``cached_blocks`` entry
        with cache_control so successive calls amortise the cost of the
        large reference data (resume corpus, rubric, etc.).
        """
        model = self.model_for(tier)
        system_blocks: list[TextBlockParam] = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ]
        for block in cached_blocks or []:
            system_blocks.append(
                {"type": "text", "text": block, "cache_control": {"type": "ephemeral"}}
            )
        messages: list[MessageParam] = [
            {"role": "user", "content": user},
        ]
        start = time.perf_counter()
        response = await self._aclient.messages.create(
            model=model,
            system=system_blocks,
            messages=messages,
            max_tokens=max_tokens or self._default_max_tokens,
            temperature=temperature,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = response.usage
        cached_in = getattr(usage, "cache_read_input_tokens", 0) or 0
        cost = _estimate_cost(model, usage.input_tokens, usage.output_tokens, cached_in)
        log.info(
            "llm_call_complete",
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached=cached_in,
            cost_usd=round(cost, 6),
            latency_ms=latency_ms,
        )
        return RouterResponse(
            text=text,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=cached_in,
            cost_usd=cost,
            latency_ms=latency_ms,
            raw=response,
        )


def _estimate_cost(model: str, input_tokens: int, output_tokens: int, cached: int) -> float:
    in_price, out_price = PRICE_TABLE.get(model, (0.0, 0.0))
    # Cached input tokens are billed at ~10% of standard input rate per
    # Anthropic's pricing as of writing.
    fresh_in = max(0, input_tokens - cached)
    return (
        fresh_in * in_price / 1_000_000
        + cached * in_price * 0.1 / 1_000_000
        + output_tokens * out_price / 1_000_000
    )


class NullModelRouter:
    """Test double — returns deterministic stub responses."""

    def __init__(self, response_text: str = '{"qualified": true, "confidence": 0.9}'):
        self.calls: list[dict[str, Any]] = []
        self._response = response_text

    def model_for(self, tier: ModelTier) -> str:
        return f"null-{tier.value}"

    async def acomplete(
        self,
        *,
        tier: ModelTier,
        system: str,
        user: str,
        cached_blocks: list[str] | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> RouterResponse:
        self.calls.append(
            {
                "tier": tier,
                "system": system,
                "user": user,
                "cached_blocks": cached_blocks,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return RouterResponse(
            text=self._response,
            model=self.model_for(tier),
            input_tokens=10,
            output_tokens=10,
            cost_usd=0.0,
            latency_ms=1,
        )
