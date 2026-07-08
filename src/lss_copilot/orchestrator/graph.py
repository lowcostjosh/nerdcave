"""DMAIC orchestration as a LangGraph state machine.

Topology:

    define -> [gate] -> measure -> analyze -> [gate] -> improve -> [gate] -> control

- Each phase node delegates to LOW/MEDIUM sub-agents and merges their
  envelopes into `LSSProjectState`.
- The HIGH-tier model is invoked in exactly one place: `analyze`'s root-cause
  synthesis. Everything else is delegation plumbing or deterministic code.
- `[gate]` nodes are LangGraph interrupts — the graph checkpoints and waits
  for a human tollgate approval before resuming (human-in-the-loop by
  construction, not convention).
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from lss_copilot.config import ModelTier
from lss_copilot.agents.data_intake import DataIntakeAgent
from lss_copilot.agents.llm import LLMClient
from lss_copilot.agents.process_mining import ProcessMiningAgent
from lss_copilot.agents.prototyping import PrototypingAgent
from lss_copilot.agents.qualitative_nlp import QualitativeNLPAgent
from lss_copilot.agents.statistical_engine import StatisticalEngineAgent
from lss_copilot.orchestrator import prompts
from lss_copilot.state.schemas import (
    AgentName,
    DMAICPhase,
    HandoffEnvelope,
    HumanGate,
    LSSProjectState,
    RootCause,
)
from pydantic import BaseModel, Field


class RootCauses(BaseModel):
    causes: list[RootCause] = Field(max_length=3)


class Orchestrator:
    """Owns the sub-agent registry and the phase-node implementations."""

    def __init__(
        self,
        llm: LLMClient,
        intake: DataIntakeAgent,
        mining: ProcessMiningAgent,
        stats: StatisticalEngineAgent,
        qualitative: QualitativeNLPAgent,
        prototyping: PrototypingAgent,
        intake_query: dict[str, Any] | None = None,
        transcripts: list[str] | None = None,
    ) -> None:
        self.llm = llm
        self.intake = intake
        self.mining = mining
        self.stats = stats
        self.qualitative = qualitative
        self.prototyping = prototyping
        self.intake_query = intake_query or {}
        self.transcripts = transcripts or []

    # ---- bookkeeping -----------------------------------------------------

    def _absorb(self, state: LSSProjectState, env: HandoffEnvelope) -> None:
        state.ledger.record(env.sender, env.input_tokens + env.output_tokens)

    # ---- phase nodes -------------------------------------------------------

    def define(self, state: LSSProjectState) -> dict:
        env = self.qualitative.draft_charter(state)
        self._absorb(state, env)
        return {"charter": env.payload, "phase": DMAICPhase.DEFINE, "ledger": state.ledger}

    def measure(self, state: LSSProjectState) -> dict:
        intake_env = self.intake.run(state, brief="Pull historical process events", **self.intake_query)
        self._absorb(state, intake_env)
        ref = intake_env.payload
        state.datasets[ref.key] = ref

        mining_env = self.mining.run(state, brief="Establish the quantitative baseline", dataset=ref)
        self._absorb(state, mining_env)
        return {
            "datasets": {ref.key: ref},
            "baseline": mining_env.payload,
            "phase": DMAICPhase.MEASURE,
            "ledger": state.ledger,
        }

    def analyze(self, state: LSSProjectState) -> dict:
        stats_env = self.stats.run(
            state,
            brief=(
                "Find what drives the CTQ metrics. Run a Pareto over defect/delay "
                "categories and regression/hypothesis tests over candidate factors. "
                f"CTQs: {state.charter.ctq_metrics if state.charter else []}"
            ),
        )
        self._absorb(state, stats_env)
        findings = stats_env.payload.root

        qual_env = self.qualitative.run(
            state, brief="Map qualitative friction to the measured bottlenecks",
            transcripts=self.transcripts,
        )
        self._absorb(state, qual_env)
        qual = qual_env.payload

        # The ONE high-reasoning call in the pipeline: cross-modal synthesis.
        synthesis, usage = self.llm.structured(
            ModelTier.HIGH,
            prompts.ORCHESTRATOR_SYSTEM,
            prompts.ROOT_CAUSE_SYNTHESIS.format(
                problem_statement=state.charter.problem_statement if state.charter else
                state.raw_problem_description,
                findings="\n".join(f.model_dump_json() for f in findings),
                bottlenecks=state.baseline.bottlenecks if state.baseline else [],
                qualitative=qual.model_dump_json(),
            ),
            RootCauses,
        )
        state.ledger.record(AgentName.ORCHESTRATOR, usage.total)
        return {
            "findings": findings,
            "fishbone": qual.fishbone,
            "fmea": qual.fmea,
            "root_causes": synthesis.causes,
            "phase": DMAICPhase.ANALYZE,
            "ledger": state.ledger,
        }

    def improve(self, state: LSSProjectState) -> dict:
        env = self.prototyping.run(
            state, brief="Draft automations eliminating the verified root causes"
        )
        self._absorb(state, env)
        return {"blueprints": env.payload.root, "phase": DMAICPhase.IMPROVE, "ledger": state.ledger}

    def control(self, state: LSSProjectState) -> dict:
        from lss_copilot.control.monitor import build_control_plan

        if state.baseline is None or state.baseline.dataset is None:
            return {"errors": [*state.errors, "control: no baseline dataset"], "phase": DMAICPhase.CONTROL}
        events = self.mining.store.get_dataframe(state.baseline.dataset)
        plan = build_control_plan(events, state.charter.ctq_metrics if state.charter else [])
        return {"control_plan": plan, "phase": DMAICPhase.CONTROL, "ledger": state.ledger}

    # ---- tollgates ---------------------------------------------------------

    @staticmethod
    def _gate(phase: DMAICPhase):
        def node(state: LSSProjectState) -> dict:
            decision = interrupt({
                "tollgate": phase.value,
                "question": f"Approve {phase.value.upper()} tollgate to proceed?",
            })
            gate = HumanGate(
                phase=phase,
                approved=bool(decision.get("approved", False)),
                reviewer=decision.get("reviewer", ""),
                comments=decision.get("comments", ""),
            )
            return {"gates": [*state.gates, gate]}
        return node


def build_graph(orchestrator: Orchestrator, checkpointer=None):
    """Compile the DMAIC graph. Interrupt-driven gates require a checkpointer."""
    graph = StateGraph(LSSProjectState)

    graph.add_node("define", orchestrator.define)
    graph.add_node("gate_define", Orchestrator._gate(DMAICPhase.DEFINE))
    graph.add_node("measure", orchestrator.measure)
    graph.add_node("analyze", orchestrator.analyze)
    graph.add_node("gate_analyze", Orchestrator._gate(DMAICPhase.ANALYZE))
    graph.add_node("improve", orchestrator.improve)
    graph.add_node("gate_improve", Orchestrator._gate(DMAICPhase.IMPROVE))
    graph.add_node("control", orchestrator.control)

    graph.set_entry_point("define")
    graph.add_edge("define", "gate_define")
    graph.add_conditional_edges(
        "gate_define",
        lambda s: "measure" if s.gate_approved(DMAICPhase.DEFINE) else END,
    )
    graph.add_edge("measure", "analyze")
    graph.add_edge("analyze", "gate_analyze")
    graph.add_conditional_edges(
        "gate_analyze",
        lambda s: "improve" if s.gate_approved(DMAICPhase.ANALYZE) else END,
    )
    graph.add_edge("improve", "gate_improve")
    graph.add_conditional_edges(
        "gate_improve",
        lambda s: "control" if s.gate_approved(DMAICPhase.IMPROVE) else END,
    )
    graph.add_edge("control", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
