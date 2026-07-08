"""Power BI streaming-dataset sink: pushes SPC rows + phase KPIs.

Create a streaming dataset in Power BI with columns
(timestamp, metric, value, ucl, lcl, center_line, alert) and set its Push URL
as LSS_POWERBI_PUSH_URL.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lss_copilot.config import settings
from lss_copilot.state.schemas import SPCAlert


class PowerBIPusher:
    def __init__(self, push_url: str | None = None) -> None:
        self.push_url = push_url or settings.powerbi_push_url
        if not self.push_url:
            raise ValueError("Power BI push URL not configured (LSS_POWERBI_PUSH_URL)")

    def push_observation(
        self, metric: str, value: float, ucl: float, lcl: float,
        center_line: float, alert: bool = False,
    ) -> None:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric": metric,
            "value": value,
            "ucl": ucl,
            "lcl": lcl,
            "center_line": center_line,
            "alert": alert,
        }
        resp = httpx.post(self.push_url, json=[row], timeout=15)
        resp.raise_for_status()

    async def alert_sink(self, alert: SPCAlert) -> None:
        """Drop-in AlertSink for SPCMonitor.add_sink()."""
        self.push_observation(
            alert.metric, alert.value, alert.ucl, alert.lcl, alert.center_line, alert=True
        )
