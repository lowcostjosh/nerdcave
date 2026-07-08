"""CSV / Excel upload connector with light auto-mapping of column names."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lss_copilot.connectors.base import Connector

# Common aliases seen in exported process data; extend as needed.
_COLUMN_ALIASES = {
    "case_id": {"case_id", "case", "id", "ticket", "ticket_id", "order_id", "issue_key"},
    "activity": {"activity", "status", "state", "step", "stage", "event"},
    "timestamp": {"timestamp", "time", "date", "created_at", "updated_at", "event_time"},
}


class FileUploadConnector(Connector):
    source_system = "upload"

    def fetch(self, path: str | Path = "", sheet: str | int = 0, **_: object) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        if p.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(p, sheet_name=sheet)
        return pd.read_csv(p)

    def to_event_log(self, raw: pd.DataFrame) -> pd.DataFrame:
        df = raw.copy()
        lowered = {c.lower().strip(): c for c in df.columns}
        renames: dict[str, str] = {}
        for target, aliases in _COLUMN_ALIASES.items():
            if target in lowered:
                renames[lowered[target]] = target
                continue
            for alias in aliases:
                if alias in lowered:
                    renames[lowered[alias]] = target
                    break
        return super().to_event_log(df.rename(columns=renames))
