"""Base sub-agent: cost tier is a class attribute, handoffs are envelopes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from lss_copilot.config import ModelTier
from lss_copilot.agents.llm import LLMClient, LLMUsage
from lss_copilot.state.schemas import AgentName, DMAICPhase, HandoffEnvelope, LSSProjectState


class SubAgent(ABC):
    """A specialist that does exactly one job and hands back a typed artifact.

    Sub-agents never see the whole conversation; they get a focused brief from
    the orchestrator plus the state slice they need. Their tier caps their
    model — token efficiency is enforced structurally, not by convention.
    """

    name: AgentName
    tier: ModelTier
    system_prompt: str = ""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    @abstractmethod
    def run(self, state: LSSProjectState, brief: str) -> HandoffEnvelope:
        """Execute the specialty and return an envelope for the orchestrator."""

    def _envelope(
        self,
        phase: DMAICPhase,
        payload: BaseModel,
        usage: LLMUsage | None = None,
        notes: str = "",
    ) -> HandoffEnvelope:
        usage = usage or LLMUsage()
        return HandoffEnvelope(
            sender=self.name,
            recipient=AgentName.ORCHESTRATOR,
            phase=phase,
            payload=payload,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model_used=usage.model,
            notes=notes,
        )

    def _ask(self, brief: str, schema: type[BaseModel]) -> tuple[BaseModel, LLMUsage]:
        if self.llm is None:
            raise RuntimeError(f"{self.name}: no LLM client injected but brief requires one")
        return self.llm.structured(self.tier, self.system_prompt, brief, schema)
