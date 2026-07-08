"""E. Code Generation & Prototyping Agent (MEDIUM tier).

When a verified root cause is a digital workflow failure, this agent drafts
the fix: a Python automation script, a Make.com/Zapier blueprint, or a small
Firebase-backed utility. Generated Python is statically checked with the same
AST gate as the sandbox before it is stored, so a blueprint that imports
requests-to-nowhere or shells out never reaches a human champion unflagged.
"""

from __future__ import annotations

from pydantic import RootModel

from lss_copilot.config import ModelTier
from lss_copilot.agents.base import SubAgent
from lss_copilot.state.schemas import (
    AgentName,
    AutomationBlueprint,
    DMAICPhase,
    HandoffEnvelope,
    LSSProjectState,
)
from lss_copilot.tools.sandbox import SandboxViolation, _static_check


class Blueprints(RootModel[list[AutomationBlueprint]]):
    pass


class PrototypingAgent(SubAgent):
    name = AgentName.PROTOTYPING
    tier = ModelTier.MEDIUM
    system_prompt = (
        "You are an automation engineer eliminating process waste. For each "
        "root cause that is a digital workflow failure, draft the smallest "
        "automation that removes it: a runnable Python script, a Make.com or "
        "Zapier blueprint (JSON), a Firebase micro-utility, or a workflow "
        "redesign. Include rollout steps and risks. Prefer boring, "
        "maintainable solutions over clever ones."
    )

    def run(self, state: LSSProjectState, brief: str) -> HandoffEnvelope:
        causes = "\n".join(
            f"- {rc.description} (confidence {rc.confidence:.0%})" for rc in state.root_causes
        )
        bottlenecks = state.baseline.bottlenecks if state.baseline else []
        blueprints, usage = self._ask(
            f"Task: {brief}\nVerified root causes:\n{causes}\n"
            f"Bottleneck transitions: {bottlenecks}\n"
            f"Goal: {state.charter.goal_statement if state.charter else ''}",
            Blueprints,
        )
        vetted: list[AutomationBlueprint] = []
        for bp in blueprints.root:
            if bp.kind == "python_script" and bp.code:
                try:
                    _static_check(bp.code)
                except (SandboxViolation, SyntaxError) as exc:
                    bp.risks.append(f"STATIC CHECK FAILED — human review required: {exc}")
            vetted.append(bp)
        return self._envelope(
            DMAICPhase.IMPROVE, Blueprints(vetted), usage,
            notes=f"{len(vetted)} blueprints drafted",
        )
