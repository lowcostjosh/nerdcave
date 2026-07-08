"""SQL connector for transaction / log tables via SQLAlchemy."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text

from lss_copilot.config import settings
from lss_copilot.connectors.base import Connector


class SQLConnector(Connector):
    source_system = "sql"

    def __init__(self, dsn: str | None = None) -> None:
        self.engine = create_engine(dsn or settings.sql_dsn)

    def fetch(self, query: str = "", params: dict | None = None, **_: object) -> pd.DataFrame:
        """Run a read-only query. Callers alias columns to the standard shape:

            SELECT order_id AS case_id, status AS activity, updated_at AS timestamp ...
        """
        if not query.lstrip().lower().startswith("select"):
            raise ValueError("SQLConnector only executes SELECT statements")
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params or {})
