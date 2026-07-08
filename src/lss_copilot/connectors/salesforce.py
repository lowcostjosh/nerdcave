"""Salesforce connector: opportunity/case history -> event log."""

from __future__ import annotations

import httpx
import pandas as pd

from lss_copilot.config import settings
from lss_copilot.connectors.base import Connector


class SalesforceConnector(Connector):
    source_system = "salesforce"
    API_VERSION = "v60.0"

    def __init__(self, instance_url: str | None = None, access_token: str | None = None) -> None:
        self.instance_url = (instance_url or settings.salesforce_instance_url).rstrip("/")
        self.token = access_token or settings.salesforce_access_token

    def fetch(self, soql: str = "", **_: object) -> pd.DataFrame:
        """Run a SOQL query (e.g. against OpportunityFieldHistory) and flatten.

        Example:
            SELECT OpportunityId, NewValue, CreatedDate
            FROM OpportunityFieldHistory WHERE Field = 'StageName'
        """
        records: list[dict] = []
        url = f"{self.instance_url}/services/data/{self.API_VERSION}/query"
        params: dict | None = {"q": soql}
        with httpx.Client(headers={"Authorization": f"Bearer {self.token}"}, timeout=30) as client:
            while url:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                for rec in data.get("records", []):
                    rec.pop("attributes", None)
                    records.append(rec)
                next_url = data.get("nextRecordsUrl")
                url = f"{self.instance_url}{next_url}" if next_url else ""
                params = None
        return pd.DataFrame(records)

    def to_event_log(self, raw: pd.DataFrame) -> pd.DataFrame:
        renames = {"OpportunityId": "case_id", "NewValue": "activity", "CreatedDate": "timestamp"}
        return super().to_event_log(raw.rename(columns=renames))
