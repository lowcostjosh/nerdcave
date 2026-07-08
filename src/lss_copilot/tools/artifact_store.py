"""Artifact store: keeps bulk data OUT of LLM context.

Dataframes, event logs, and generated files are parked here and referenced by
key (`DataSourceRef.key`). Agents exchange handles, never payloads — this is
the single biggest token-burn control in the system. The default backend is
local parquet; swap `ArtifactStore` for an S3/GCS implementation in prod.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from lss_copilot.state.schemas import DataSourceRef


class ArtifactStore:
    def __init__(self, root: str | Path = ".lss_artifacts") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_dataframe(self, df: pd.DataFrame, source_system: str, name: str) -> DataSourceRef:
        key = f"{name}.parquet"
        path = self.root / key
        df.to_parquet(path, index=False)
        fingerprint = hashlib.sha256(
            json.dumps({c: str(t) for c, t in df.dtypes.items()}, sort_keys=True).encode()
        ).hexdigest()[:16]
        return DataSourceRef(
            key=key,
            source_system=source_system,
            row_count=len(df),
            columns=list(df.columns),
            schema_fingerprint=fingerprint,
        )

    def get_dataframe(self, ref: DataSourceRef) -> pd.DataFrame:
        path = self.root / ref.key
        if not path.exists():
            raise FileNotFoundError(f"artifact '{ref.key}' not found in {self.root}")
        return pd.read_parquet(path)

    def put_text(self, text: str, name: str) -> str:
        path = self.root / name
        path.write_text(text)
        return name

    def get_text(self, name: str) -> str:
        return (self.root / name).read_text()
