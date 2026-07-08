"""CONTROL phase: live SPC monitoring.

`build_control_plan` freezes UCL/LCL from the improved-process baseline;
`SPCMonitor` re-polls the source connector on an interval, evaluates the
Western Electric rules, and fans alerts out to registered sinks (dashboard
push, email/Slack hooks). Pure asyncio — no LLM tokens are spent in CONTROL
unless a human asks for an interpretation.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import pandas as pd

from lss_copilot.config import settings
from lss_copilot.connectors.base import Connector
from lss_copilot.state.schemas import ControlPlan, SPCAlert
from lss_copilot.stats.spc import control_limits, evaluate_spc_rules

logger = logging.getLogger(__name__)

AlertSink = Callable[[SPCAlert], Awaitable[None]]


def daily_metric_series(events: pd.DataFrame) -> dict[str, list[float]]:
    """Derive the standard monitored series from an event log:
    daily mean cycle time (hours) and daily throughput (cases closed)."""
    df = events.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    per_case = df.groupby("case_id")["timestamp"].agg(["min", "max"])
    per_case["cycle_hours"] = (per_case["max"] - per_case["min"]).dt.total_seconds() / 3600
    per_case["closed_day"] = per_case["max"].dt.floor("D")
    daily = per_case.groupby("closed_day").agg(
        cycle_time_hours=("cycle_hours", "mean"),
        throughput=("cycle_hours", "size"),
    )
    return {
        "cycle_time_hours": daily["cycle_time_hours"].tolist(),
        "throughput": daily["throughput"].astype(float).tolist(),
    }


def build_control_plan(
    baseline_events: pd.DataFrame,
    ctq_metrics: list[str] | None = None,
    poll_interval_seconds: int | None = None,
) -> ControlPlan:
    series = daily_metric_series(baseline_events)
    plan = ControlPlan(
        poll_interval_seconds=poll_interval_seconds or settings.spc_poll_interval_seconds,
        response_plan=(
            "On any alert: freeze the change pipeline, notify the process "
            "champion, run 5-Whys on the alerting window, document in the "
            "project register before resuming."
        ),
    )
    for metric, values in series.items():
        if len(values) < 2:
            continue
        limits = control_limits(values)
        plan.monitored_metrics.append(metric)
        plan.center_line[metric] = limits["center_line"]
        plan.ucl[metric] = limits["ucl"]
        plan.lcl[metric] = limits["lcl"]
    if ctq_metrics:
        plan.response_plan += f" CTQ watch list: {', '.join(ctq_metrics)}."
    return plan


class SPCMonitor:
    def __init__(self, connector: Connector, plan: ControlPlan, query: dict | None = None) -> None:
        self.connector = connector
        self.plan = plan
        self.query = query or {}
        self.sinks: list[AlertSink] = []
        self._stop = asyncio.Event()

    def add_sink(self, sink: AlertSink) -> None:
        self.sinks.append(sink)

    def stop(self) -> None:
        self._stop.set()

    def check_once(self, events: pd.DataFrame) -> list[SPCAlert]:
        alerts: list[SPCAlert] = []
        series = daily_metric_series(events)
        for metric in self.plan.monitored_metrics:
            values = series.get(metric, [])
            if not values:
                continue
            limits = {
                "center_line": self.plan.center_line[metric],
                "ucl": self.plan.ucl[metric],
                "lcl": self.plan.lcl[metric],
            }
            alerts.extend(evaluate_spc_rules(metric, values, limits))
        self.plan.alerts.extend(alerts)
        return alerts

    async def run(self) -> None:
        """Poll -> evaluate -> alert, forever (until .stop())."""
        while not self._stop.is_set():
            try:
                raw = await asyncio.to_thread(self.connector.fetch, **self.query)
                events = self.connector.to_event_log(raw)
                for alert in self.check_once(events):
                    logger.warning("SPC alert: %s %s", alert.metric, alert.message)
                    for sink in self.sinks:
                        await sink(alert)
            except Exception:  # keep the watchdog alive through transient failures
                logger.exception("SPC poll failed; retrying next interval")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.plan.poll_interval_seconds
                )
            except TimeoutError:
                pass
