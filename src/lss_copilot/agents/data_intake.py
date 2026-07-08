"""A. Data Intake & Pipelining Agent (LOW tier).

Almost all of this agent's work is deterministic code: connectors pull, the
base class normalizes, the artifact store parks the dataframe. The LLM is
touched only when a source's columns can't be auto-mapped — and then only the
column *names* (never rows) are sent, at the LOW tier.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

from lss_copilot.config import ModelTier
from lss_copilot.agents.base import SubAgent
from lss_copilot.connectors.base import Connector
from lss_copilot.state.schemas import AgentName, DMAICPhase, HandoffEnvelope, LSSProjectState
from lss_copilot.tools.artifact_store import ArtifactStore


class ColumnMapping(BaseModel):
    """LLM output when auto-mapping fails: raw column -> standard column."""

    case_id: str = Field(description="raw column holding the case/ticket identifier")
    activity: str = Field(description="raw column holding the process step / status")
    timestamp: str = Field(description="raw column holding the event time")


class DataIntakeAgent(SubAgent):
    name = AgentName.DATA_INTAKE
    tier = ModelTier.LOW
    system_prompt = (
        "You map raw data column names onto a standard process event log "
        "(case_id, activity, timestamp). Answer only with the mapping."
    )

    def __init__(self, connector: Connector, store: ArtifactStore, llm=None) -> None:
        super().__init__(llm)
        self.connector = connector
        self.store = store

    def run(self, state: LSSProjectState, brief: str, **query: object) -> HandoffEnvelope:
        raw = self.connector.fetch(**query)
        usage = None
        try:
            events = self.connector.to_event_log(raw)
        except ValueError:
            # Deterministic mapping failed; ask the LOW-tier model using
            # column names + dtypes only. Zero data rows leave the process.
            schema_desc = ", ".join(f"{c} ({t})" for c, t in raw.dtypes.items())
            mapping, usage = self._ask(
                f"Task: {brief}\nRaw columns: {schema_desc}\n"
                "Map them to case_id / activity / timestamp.",
                ColumnMapping,
            )
            renamed = raw.rename(columns={
                mapping.case_id: "case_id",
                mapping.activity: "activity",
                mapping.timestamp: "timestamp",
            })
            events = Connector.to_event_log(self.connector, renamed)

        events = self._clean(events)
        ref = self.store.put_dataframe(
            events, self.connector.source_system,
            name=f"{state.project_id}_{self.connector.source_system}_events",
        )
        return self._envelope(
            DMAICPhase.MEASURE, ref, usage,
            notes=f"Ingested {ref.row_count} events from {self.connector.source_system}",
        )

    @staticmethod
    def _clean(events: pd.DataFrame) -> pd.DataFrame:
        events = events.drop_duplicates(subset=["case_id", "activity", "timestamp"])
        # Drop cases with a single event: no transitions to mine.
        counts = events.groupby("case_id")["activity"].transform("count")
        return events[counts > 1].reset_index(drop=True)
