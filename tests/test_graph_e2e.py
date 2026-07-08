"""End-to-end DMAIC graph run with a stub LLM (no network, no API key).

Exercises: intake -> mining -> stats plan execution -> qualitative -> HIGH-tier
synthesis -> prototyping -> control plan, with human tollgates resumed via
LangGraph Command(resume=...).
"""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("langgraph")

from langgraph.types import Command
from pydantic import BaseModel

from lss_copilot.config import ModelTier
from lss_copilot.agents.data_intake import DataIntakeAgent
from lss_copilot.agents.llm import LLMUsage
from lss_copilot.agents.process_mining import ProcessMiningAgent, ValueAddClassification
from lss_copilot.agents.prototyping import Blueprints, PrototypingAgent
from lss_copilot.agents.qualitative_nlp import QualitativeAnalysis, QualitativeNLPAgent
from lss_copilot.agents.statistical_engine import (
    AnalysisPlan,
    PlannedTest,
    StatisticalEngineAgent,
)
from lss_copilot.connectors.file_upload import FileUploadConnector
from lss_copilot.orchestrator.graph import Orchestrator, RootCauses, build_graph
from lss_copilot.state.schemas import (
    AutomationBlueprint,
    DMAICPhase,
    FishboneDiagram,
    FMEAEntry,
    LSSProjectState,
    ProjectCharter,
    RootCause,
    SIPOCMap,
)
from lss_copilot.tools.artifact_store import ArtifactStore


class StubLLM:
    """Deterministic LLMClient: returns canned artifacts per schema, tracks tiers."""

    def __init__(self) -> None:
        self.calls: list[tuple[ModelTier, str]] = []

    def structured(self, tier, system, user, schema):
        self.calls.append((tier, schema.__name__))
        usage = LLMUsage(input_tokens=100, output_tokens=50, model=f"stub-{tier}")
        artifact = self._make(schema)
        return artifact, usage

    @staticmethod
    def _make(schema: type[BaseModel]) -> BaseModel:
        if schema is ProjectCharter:
            return ProjectCharter(
                title="Reduce ticket resolution time",
                problem_statement="Resolution takes 32h on average vs 8h target",
                goal_statement="Cut mean resolution time to 8h within one quarter",
                sipoc=SIPOCMap(process_steps=["Created", "Triage", "Fix", "Done"]),
                ctq_metrics=["cycle_time_hours"],
            )
        if schema is ValueAddClassification:
            return ValueAddClassification(
                value_add=["Fix", "Done"], non_value_add=["Triage", "Reopened"]
            )
        if schema is AnalysisPlan:
            # Planned against the case feature table the engine now defaults to.
            return AnalysisPlan([
                PlannedTest(kind="describe", target_metric="cycle_hours"),
                PlannedTest(kind="pareto", target_metric="count", group_by="reworked"),
            ])
        if schema is QualitativeAnalysis:
            return QualitativeAnalysis(
                fishbone=FishboneDiagram(
                    effect="Slow resolution",
                    causes={"Method": ["No triage SLA"], "Man": ["Single approver"]},
                ),
                fmea=[FMEAEntry(
                    failure_mode="Tickets idle in triage", effect="SLA breach",
                    cause="No routing rule", severity=8, occurrence=7, detection=3,
                )],
            )
        if schema is RootCauses:
            return RootCauses(causes=[RootCause(
                description="Triage queue has no routing rule; work idles 28h",
                confidence=0.85,
            )])
        if schema is Blueprints:
            return Blueprints([AutomationBlueprint(
                title="Auto-route triage by component",
                root_cause_addressed="Triage queue has no routing rule",
                kind="python_script",
                summary="Webhook that assigns tickets on creation",
                code="import json\nresult = {'ok': True}\n",
            )])
        raise AssertionError(f"stub has no factory for {schema.__name__}")


@pytest.fixture
def event_csv(tmp_path):
    rows = []
    base = pd.Timestamp("2026-01-05", tz="UTC")
    for i in range(12):
        t = base + pd.Timedelta(days=i)
        for act, offset in [("Created", 0), ("Triage", 2), ("Fix", 30), ("Done", 32)]:
            rows.append({"case_id": f"C{i}", "activity": act,
                         "timestamp": (t + pd.Timedelta(hours=offset)).isoformat()})
    path = tmp_path / "events.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_full_dmaic_run(event_csv, tmp_path):
    llm = StubLLM()
    store = ArtifactStore(tmp_path / "artifacts")
    orchestrator = Orchestrator(
        llm=llm,
        intake=DataIntakeAgent(FileUploadConnector(), store, llm=llm),
        mining=ProcessMiningAgent(store, llm=llm),
        stats=StatisticalEngineAgent(store, llm=llm),
        qualitative=QualitativeNLPAgent(llm=llm),
        prototyping=PrototypingAgent(llm=llm),
        intake_query={"path": str(event_csv)},
        transcripts=["Support says tickets sit unassigned for a day."],
    )
    app = build_graph(orchestrator)
    config = {"configurable": {"thread_id": "t1"}}

    state = LSSProjectState(project_id="proj1", raw_problem_description="tickets too slow")
    result = app.invoke(state, config)

    # Walk through all three human tollgates, approving each.
    gates_seen = []
    while "__interrupt__" in result:
        gates_seen.append(result["__interrupt__"][0].value["tollgate"])
        result = app.invoke(Command(resume={"approved": True, "reviewer": "test"}), config)

    final = LSSProjectState.model_validate(result)
    assert gates_seen == ["define", "analyze", "improve"]
    assert final.phase == DMAICPhase.CONTROL

    # DEFINE
    assert final.charter and final.charter.ctq_metrics == ["cycle_time_hours"]
    # MEASURE: deterministic mining on the CSV
    assert final.baseline is not None
    assert final.baseline.mean_cycle_time_hours == pytest.approx(32.0)
    assert "Triage -> Fix" in final.baseline.bottlenecks
    assert final.baseline.value_stream_mermaid.startswith("flowchart")
    assert 0 < final.baseline.process_cycle_efficiency < 1
    # ANALYZE: deterministic execution on the auto-built feature table
    described = next(f for f in final.findings if f.test_name == "descriptive")
    assert described.statistic == pytest.approx(32.0)  # true planted cycle time
    assert any(f.test_name == "pareto" for f in final.findings)
    assert final.baseline.feature_table is not None
    assert final.baseline.feature_table.key in final.datasets
    assert len(final.root_causes) == 1 and final.root_causes[0].confidence == 0.85
    assert final.fmea[0].rpn == 8 * 7 * 3
    # IMPROVE
    assert final.blueprints and final.blueprints[0].kind == "python_script"
    # CONTROL
    assert final.control_plan and "cycle_time_hours" in final.control_plan.monitored_metrics

    # Token-efficiency invariant: exactly ONE high-tier call (root-cause synthesis).
    high_calls = [name for tier, name in llm.calls if tier == ModelTier.HIGH]
    assert high_calls == ["RootCauses"]
    assert final.ledger.total == 150 * len(llm.calls)


def test_rejected_gate_halts_pipeline(event_csv, tmp_path):
    llm = StubLLM()
    store = ArtifactStore(tmp_path / "artifacts")
    orchestrator = Orchestrator(
        llm=llm,
        intake=DataIntakeAgent(FileUploadConnector(), store, llm=llm),
        mining=ProcessMiningAgent(store, llm=llm),
        stats=StatisticalEngineAgent(store, llm=llm),
        qualitative=QualitativeNLPAgent(llm=llm),
        prototyping=PrototypingAgent(llm=llm),
        intake_query={"path": str(event_csv)},
    )
    app = build_graph(orchestrator)
    config = {"configurable": {"thread_id": "t2"}}

    state = LSSProjectState(project_id="proj2", raw_problem_description="slow")
    result = app.invoke(state, config)
    assert "__interrupt__" in result
    result = app.invoke(Command(resume={"approved": False, "reviewer": "test"}), config)

    final = LSSProjectState.model_validate(result)
    assert final.phase == DMAICPhase.DEFINE  # never advanced past the gate
    assert final.baseline is None
