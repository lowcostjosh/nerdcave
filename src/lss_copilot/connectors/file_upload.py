"""CSV / Excel upload connector with light auto-mapping of column names."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lss_copilot.connectors.base import Connector

# Common aliases seen in exported process data, in priority order; extend as needed.
_COLUMN_ALIASES = {
    "case_id": ["case_id", "case", "ticket_id", "ticket", "issue_key", "order_id", "id"],
    "activity": ["activity", "status", "state", "stage", "step", "event"],
    "timestamp": ["timestamp", "event_time", "updated_at", "created_at", "time", "date"],
}


def _normalize(name: str) -> str:
    """'Ticket ID' / 'ticket-id' / ' Ticket_Id ' -> 'ticket_id'."""
    return name.strip().lower().replace("-", "_").replace(" ", "_")


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
        normalized = {}
        for col in df.columns:  # first occurrence wins on collision
            normalized.setdefault(_normalize(col), col)
        renames: dict[str, str] = {}
        claimed: set[str] = set()
        for target, aliases in _COLUMN_ALIASES.items():
            for alias in [target, *aliases]:
                raw_col = normalized.get(alias)
                if raw_col is not None and raw_col not in claimed:
                    renames[raw_col] = target
                    claimed.add(raw_col)
                    break
        return super().to_event_log(df.rename(columns=renames))
