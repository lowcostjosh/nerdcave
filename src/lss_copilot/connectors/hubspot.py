"""HubSpot connector: deal stage history -> event log."""

from __future__ import annotations

import httpx
import pandas as pd

from lss_copilot.config import settings
from lss_copilot.connectors.base import Connector


class HubSpotConnector(Connector):
    source_system = "hubspot"
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, access_token: str | None = None) -> None:
        self.token = access_token or settings.hubspot_access_token

    def fetch(self, object_type: str = "deals", limit: int = 1000, **_: object) -> pd.DataFrame:
        """Pull objects with `dealstage` property history via propertiesWithHistory."""
        rows: list[dict] = []
        after: str | None = None
        headers = {"Authorization": f"Bearer {self.token}"}
        with httpx.Client(base_url=self.BASE_URL, headers=headers, timeout=30) as client:
            while len(rows) < limit:
                params: dict = {
                    "limit": 100,
                    "propertiesWithHistory": "dealstage",
                }
                if after:
                    params["after"] = after
                resp = client.get(f"/crm/v3/objects/{object_type}", params=params)
                resp.raise_for_status()
                data = resp.json()
                for obj in data.get("results", []):
                    history = (obj.get("propertiesWithHistory") or {}).get("dealstage", [])
                    for version in history:
                        rows.append({
                            "case_id": obj["id"],
                            "activity": version.get("value"),
                            "timestamp": version.get("timestamp"),
                            "actor": version.get("updatedByUserId"),
                        })
                after = (data.get("paging", {}).get("next") or {}).get("after")
                if not after:
                    break
        return pd.DataFrame(rows)
