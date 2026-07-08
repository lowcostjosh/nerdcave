"""B. Process Mining & Mapping Agent (MEDIUM tier).

Mining itself is deterministic (lss_copilot.mining). The MEDIUM model is used
for one thing only: classifying which activities are value-add vs waste so PCE
can be computed — a judgment call that needs domain reasoning but not the
high tier. Everything else (variants, loops, bottlenecks, Mermaid VSM) is code.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from lss_copilot.config import ModelTier
from lss_copilot.agents.base import SubAgent
from lss_copilot.mining.features import case_feature_table
from lss_copilot.mining.process_mining import mine_process, process_cycle_efficiency
from lss_copilot.state.schemas import (
    AgentName,
    DataSourceRef,
    DMAICPhase,
    HandoffEnvelope,
    LSSProjectState,
    ProcessBaseline,
)
from lss_copilot.tools.artifact_store import ArtifactStore


class ValueAddClassification(BaseModel):
    value_add: list[str] = Field(description="activities the customer would pay for")
    non_value_add: list[str] = Field(description="waste: waiting, rework, handoffs")


class ProcessMiningAgent(SubAgent):
    name = AgentName.PROCESS_MINING
    tier = ModelTier.MEDIUM
    system_prompt = (
        "You are a Lean value-stream analyst. Given process activities and the "
        "project charter, classify each as value-add or non-value-add."
    )

    def __init__(self, store: ArtifactStore, llm=None, defect_activities: set[str] | None = None) -> None:
        super().__init__(llm)
        self.store = store
        self.defect_activities = defect_activities or {"Rejected", "Reopened", "Failed", "Returned"}

    def run(self, state: LSSProjectState, brief: str, dataset: DataSourceRef | None = None) -> HandoffEnvelope:
        ref = dataset or next(iter(state.datasets.values()), None)
        if ref is None:
            raise ValueError("process mining requires an ingested dataset")
        events = self.store.get_dataframe(ref)
        model = mine_process(events)

        usage = None
        if self.llm is not None and model.activities:
            classification, usage = self._ask(
                f"Charter goal: {state.charter.goal_statement if state.charter else brief}\n"
                f"Activities observed: {model.activities}",
                ValueAddClassification,
            )
            va_set = set(classification.value_add)
        else:
            va_set = set(model.activities)  # degenerate fallback: PCE = 1.0 flagged in notes

        # Time spent *entering* a value-add activity counts as value-add time.
        va_hours = sum(
            h * model.transition_counts[t]
            for t, h in model.transition_mean_hours.items() if t[1] in va_set
        )
        total_hours = sum(
            h * model.transition_counts[t] for t, h in model.transition_mean_hours.items()
        )
        pce = process_cycle_efficiency(va_hours, total_hours) if total_hours else 0.0

        n_cases = events["case_id"].nunique()
        defect_cases = events[events["activity"].isin(self.defect_activities)]["case_id"].nunique()
        span_days = max(
            (events["timestamp"].max() - events["timestamp"].min()).total_seconds() / 86400, 1e-9
        )

        mermaid = model.to_mermaid()
        self.store.put_text(mermaid, f"{state.project_id}_vsm.mmd")

        # Roll the log up to one row per case so ANALYZE can regress the Y
        # (cycle_hours) against candidate X's (attributes, dwell times).
        features = case_feature_table(events)
        feature_ref = self.store.put_dataframe(
            features, ref.source_system, name=f"{state.project_id}_case_features"
        )

        baseline = ProcessBaseline(
            mean_cycle_time_hours=model.mean_cycle_time_hours,
            median_cycle_time_hours=model.median_cycle_time_hours,
            defect_rate=defect_cases / n_cases if n_cases else 0.0,
            throughput_per_day=n_cases / span_days,
            process_cycle_efficiency=pce,
            value_stream_mermaid=mermaid,
            bottlenecks=[f"{a} -> {b}" for a, b in model.bottlenecks],
            rework_loops=[f"{a} -> {b} (revisit)" for a, b in model.rework_loops],
            variant_count=len(model.variants),
            dataset=ref,
            feature_table=feature_ref,
        )
        notes = f"Mined {n_cases} cases, {len(model.variants)} variants"
        if usage is None:
            notes += " (no LLM: all activities assumed value-add — supply llm for real PCE)"
        return self._envelope(DMAICPhase.MEASURE, baseline, usage, notes=notes)
