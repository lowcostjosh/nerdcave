"""Tier-enforced LLM access.

Every LLM call in the platform goes through `LLMRouter.structured()`:
  - the caller declares its ModelTier; the router maps tier -> model, so a
    sub-agent physically cannot burn high-tier tokens,
  - output is forced through a Pydantic schema via tool-use, so downstream
    consumers always get validated artifacts, never prose,
  - token usage is returned for the orchestrator's ledger.

`LLMClient` is a Protocol so tests (and offline runs) can inject a stub.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from lss_copilot.config import ModelTier, settings

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMClient(Protocol):
    def structured(
        self, tier: ModelTier, system: str, user: str, schema: type[T]
    ) -> tuple[T, LLMUsage]: ...


class AnthropicRouter:
    """Production client backed by the Anthropic API with structured output."""

    def __init__(self, api_key: str | None = None) -> None:
        import anthropic  # deferred so offline tests never need the SDK configured

        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)

    def structured(
        self, tier: ModelTier, system: str, user: str, schema: type[T]
    ) -> tuple[T, LLMUsage]:
        model = settings.model_for(tier)
        tool = {
            "name": "emit",
            "description": f"Emit the {schema.__name__} artifact.",
            "input_schema": schema.model_json_schema(),
        }
        message = self._client.messages.create(
            model=model,
            max_tokens=settings.max_tokens_for(tier),
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
        )
        payload = next(b.input for b in message.content if b.type == "tool_use")
        usage = LLMUsage(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=model,
        )
        return schema.model_validate(payload), usage
