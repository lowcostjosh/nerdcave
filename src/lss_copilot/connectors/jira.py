"""Jira connector: issues + changelog -> event log of status transitions."""

from __future__ import annotations

import httpx
import pandas as pd

from lss_copilot.config import settings
from lss_copilot.connectors.base import Connector


class JiraConnector(Connector):
    source_system = "jira"

    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.jira_base_url).rstrip("/")
        self.auth = (email or settings.jira_email, api_token or settings.jira_api_token)

    def fetch(self, jql: str = "", max_results: int = 1000, **_: object) -> pd.DataFrame:
        """Pull issues with changelogs. Each status change becomes one event."""
        rows: list[dict] = []
        start_at = 0
        with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=30) as client:
            while start_at < max_results:
                resp = client.get(
                    "/rest/api/3/search",
                    params={
                        "jql": jql,
                        "expand": "changelog",
                        "startAt": start_at,
                        "maxResults": min(100, max_results - start_at),
                        "fields": "created,status,assignee,issuetype",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for issue in data.get("issues", []):
                    key = issue["key"]
                    fields = issue["fields"]
                    rows.append({
                        "case_id": key,
                        "activity": "Created",
                        "timestamp": fields["created"],
                        "actor": None,
                        "issue_type": fields.get("issuetype", {}).get("name"),
                    })
                    for history in issue.get("changelog", {}).get("histories", []):
                        for item in history.get("items", []):
                            if item.get("field") == "status":
                                rows.append({
                                    "case_id": key,
                                    "activity": item.get("toString", "Unknown"),
                                    "timestamp": history["created"],
                                    "actor": history.get("author", {}).get("displayName"),
                                    "issue_type": fields.get("issuetype", {}).get("name"),
                                })
                fetched = start_at + len(data.get("issues", []))
                if fetched >= data.get("total", 0) or not data.get("issues"):
                    break
                start_at = fetched
        return pd.DataFrame(rows)
