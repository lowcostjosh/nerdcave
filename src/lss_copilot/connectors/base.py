"""Connector contract for the Data Intake agent.

Every connector returns a *standardized event log* dataframe so downstream
agents (mining, stats) never care where data came from:

    case_id | activity | timestamp | actor? | attributes...

Connectors are deterministic code — no LLM involvement in extraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

STANDARD_COLUMNS = ["case_id", "activity", "timestamp"]


class Connector(ABC):
    source_system: str = "unknown"

    @abstractmethod
    def fetch(self, **query: object) -> pd.DataFrame:
        """Pull raw records from the source system."""

    def to_event_log(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Normalize to the standard event-log shape. Override per source."""
        missing = [c for c in STANDARD_COLUMNS if c not in raw.columns]
        if missing:
            raise ValueError(
                f"{self.source_system}: cannot normalize, missing columns {missing}"
            )
        df = raw.copy()
        # format="mixed": real exports mix precisions/offsets row to row.
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
        df = df.dropna(subset=STANDARD_COLUMNS)
        df["case_id"] = df["case_id"].astype(str)
        df["activity"] = df["activity"].astype(str).str.strip()
        return df.sort_values(["case_id", "timestamp"]).reset_index(drop=True)
