"""Canonical state schemas shared by the orchestrator and every sub-agent.

Every handoff between agents is a validated `HandoffEnvelope` carrying one of
these Pydantic models. Sub-agents never pass free-form prose to each other —
prose is for humans; agents exchange typed artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, Field, computed_field, field_validator


class DMAICPhase(StrEnum):
    DEFINE = "define"
    MEASURE = "measure"
    ANALYZE = "analyze"
    IMPROVE = "improve"
    CONTROL = "control"


class AgentName(StrEnum):
    ORCHESTRATOR = "orchestrator"
    DATA_INTAKE = "data_intake"
    PROCESS_MINING = "process_mining"
    STATISTICAL_ENGINE = "statistical_engine"
    QUALITATIVE_NLP = "qualitative_nlp"
    PROTOTYPING = "prototyping"


# --------------------------------------------------------------------------
# DEFINE artifacts
# --------------------------------------------------------------------------

class SIPOCMap(BaseModel):
    suppliers: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list, max_length=7)
    outputs: list[str] = Field(default_factory=list)
    customers: list[str] = Field(default_factory=list)


class ProjectCharter(BaseModel):
    title: str
    problem_statement: str = Field(description="Quantified pain: what, where, when, how much")
    goal_statement: str = Field(description="SMART goal with target metric and deadline")
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    business_impact: str = ""
    champion: str = ""
    sipoc: SIPOCMap = Field(default_factory=SIPOCMap)
    ctq_metrics: list[str] = Field(
        default_factory=list, description="Critical-to-quality output metrics (the project Y's)"
    )


# --------------------------------------------------------------------------
# MEASURE artifacts
# --------------------------------------------------------------------------

class DataSourceRef(BaseModel):
    """Pointer to a normalized dataset produced by the Data Intake agent.

    Dataframes never travel through LLM context. They are parked in the
    artifact store and referenced by key — agents pass this handle around.
    """

    key: str = Field(description="Artifact-store key of the parquet/JSON payload")
    source_system: str = Field(description="jira | sql | salesforce | hubspot | upload")
    row_count: int = 0
    columns: list[str] = Field(default_factory=list)
    schema_fingerprint: str = ""
    pulled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessBaseline(BaseModel):
    """Quantitative 'as-is' picture produced in MEASURE."""

    mean_cycle_time_hours: float
    median_cycle_time_hours: float
    defect_rate: float = Field(ge=0.0, le=1.0)
    throughput_per_day: float
    process_cycle_efficiency: float = Field(
        ge=0.0, le=1.0, description="PCE = value-add time / total lead time"
    )
    value_stream_mermaid: str = Field(default="", description="Mermaid.js VSM diagram source")
    bottlenecks: list[str] = Field(default_factory=list)
    rework_loops: list[str] = Field(default_factory=list)
    variant_count: int = 0
    dataset: DataSourceRef | None = None


# --------------------------------------------------------------------------
# ANALYZE artifacts
# --------------------------------------------------------------------------

class StatisticalFinding(BaseModel):
    """One deterministic result from the Statistical Engine. No narrative —
    the orchestrator writes the narrative; this stays pure math."""

    test_name: str = Field(description="e.g. one_way_anova, welch_t_test, chi_square, ols")
    target_metric: str
    factors: list[str] = Field(default_factory=list)
    statistic: float
    p_value: float = Field(ge=0.0, le=1.0)
    effect_size: float | None = None
    confidence_level: float = 0.95
    significant: bool
    details: dict[str, Any] = Field(default_factory=dict)


class FishboneDiagram(BaseModel):
    """Ishikawa diagram keyed by the classic 6M categories."""

    effect: str
    causes: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "Man": [], "Machine": [], "Method": [], "Material": [], "Measurement": [], "Milieu": []
        }
    )

    def to_mermaid(self) -> str:
        lines = ["mindmap", f"  root(({self.effect}))"]
        for category, items in self.causes.items():
            if not items:
                continue
            lines.append(f"    {category}")
            lines.extend(f"      {item}" for item in items)
        return "\n".join(lines)


class FMEAEntry(BaseModel):
    failure_mode: str
    effect: str
    cause: str
    severity: int = Field(ge=1, le=10)
    occurrence: int = Field(ge=1, le=10)
    detection: int = Field(ge=1, le=10, description="10 = impossible to detect")
    recommended_action: str = ""

    @computed_field  # RPN is derived, never LLM-supplied
    @property
    def rpn(self) -> int:
        return self.severity * self.occurrence * self.detection


class RootCause(BaseModel):
    """A verified root cause: qualitative signal cross-validated by math."""

    description: str
    supporting_findings: list[StatisticalFinding] = Field(default_factory=list)
    fmea_entries: list[FMEAEntry] = Field(default_factory=list)
    pareto_contribution: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Share of total defects/delay attributable"
    )
    confidence: float = Field(ge=0.0, le=1.0)


# --------------------------------------------------------------------------
# IMPROVE artifacts
# --------------------------------------------------------------------------

class AutomationBlueprint(BaseModel):
    """Output of the Prototyping agent for one improvement action."""

    title: str
    root_cause_addressed: str
    kind: str = Field(description="python_script | make_blueprint | zapier_blueprint | firebase_utility | workflow_redesign")
    summary: str
    code: str = Field(default="", description="Runnable script or JSON blueprint body")
    estimated_hours_saved_per_week: float | None = None
    rollout_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# CONTROL artifacts
# --------------------------------------------------------------------------

class SPCAlert(BaseModel):
    metric: str
    rule: str = Field(description="Which control rule fired, e.g. beyond_3_sigma, run_of_8")
    value: float
    ucl: float
    lcl: float
    center_line: float
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""


class ControlPlan(BaseModel):
    monitored_metrics: list[str] = Field(default_factory=list)
    ucl: dict[str, float] = Field(default_factory=dict)
    lcl: dict[str, float] = Field(default_factory=dict)
    center_line: dict[str, float] = Field(default_factory=dict)
    poll_interval_seconds: int = 300
    response_plan: str = ""
    alerts: list[SPCAlert] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Handoff envelope + human gates
# --------------------------------------------------------------------------

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class HandoffEnvelope(BaseModel, Generic[PayloadT]):
    """Typed contract for every inter-agent handoff.

    The orchestrator only ever sees envelopes; token accounting rides along so
    the router can rebalance tier assignments over time.
    """

    sender: AgentName
    recipient: AgentName
    phase: DMAICPhase
    payload: PayloadT
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str = ""
    notes: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HumanGate(BaseModel):
    """Tollgate review between DMAIC phases: humans approve, agents proceed."""

    phase: DMAICPhase
    approved: bool = False
    reviewer: str = ""
    comments: str = ""


# --------------------------------------------------------------------------
# The graph state
# --------------------------------------------------------------------------

def _merge_dicts(left: dict, right: dict) -> dict:
    return {**left, **right}


class TokenLedger(BaseModel):
    """Running spend per agent so tier routing decisions are observable."""

    by_agent: dict[str, int] = Field(default_factory=dict)

    def record(self, agent: AgentName, tokens: int) -> None:
        self.by_agent[agent.value] = self.by_agent.get(agent.value, 0) + tokens

    @property
    def total(self) -> int:
        return sum(self.by_agent.values())


class LSSProjectState(BaseModel):
    """Single source of truth threaded through the LangGraph state machine.

    Sub-agents receive only the slice they need and return envelopes; the
    orchestrator's reducer merges results back here.
    """

    project_id: str
    raw_problem_description: str
    phase: DMAICPhase = DMAICPhase.DEFINE

    # Phase artifacts
    charter: ProjectCharter | None = None
    datasets: Annotated[dict[str, DataSourceRef], _merge_dicts] = Field(default_factory=dict)
    baseline: ProcessBaseline | None = None
    findings: list[StatisticalFinding] = Field(default_factory=list)
    fishbone: FishboneDiagram | None = None
    fmea: list[FMEAEntry] = Field(default_factory=list)
    root_causes: list[RootCause] = Field(default_factory=list)  # capped to 3 by validator
    blueprints: list[AutomationBlueprint] = Field(default_factory=list)
    control_plan: ControlPlan | None = None

    # Governance & accounting
    gates: list[HumanGate] = Field(default_factory=list)
    ledger: TokenLedger = Field(default_factory=TokenLedger)
    errors: list[str] = Field(default_factory=list)

    @field_validator("root_causes")
    @classmethod
    def _cap_root_causes(cls, v: list[RootCause]) -> list[RootCause]:
        # ANALYZE contract: present humans the top 3 verified causes, ranked.
        return sorted(v, key=lambda rc: rc.confidence, reverse=True)[:3]

    def gate_approved(self, phase: DMAICPhase) -> bool:
        return any(g.phase == phase and g.approved for g in self.gates)
