import pandas as pd

from lss_copilot.control.monitor import build_control_plan, daily_metric_series


def _events(n_days: int = 30, cycle_hours: float = 24.0) -> pd.DataFrame:
    rows = []
    base = pd.Timestamp("2026-01-01", tz="UTC")
    for i in range(n_days):
        start = base + pd.Timedelta(days=i)
        # tiny deterministic jitter so moving range (sigma estimate) is nonzero
        end = start + pd.Timedelta(hours=cycle_hours + (i % 3))
        rows += [
            {"case_id": f"C{i}", "activity": "Created", "timestamp": start},
            {"case_id": f"C{i}", "activity": "Done", "timestamp": end},
        ]
    return pd.DataFrame(rows)


def test_daily_series_shape():
    series = daily_metric_series(_events())
    assert set(series) == {"cycle_time_hours", "throughput"}
    assert len(series["throughput"]) > 0


def test_control_plan_freezes_limits():
    plan = build_control_plan(_events(), ctq_metrics=["resolution time"])
    assert "cycle_time_hours" in plan.monitored_metrics
    m = "cycle_time_hours"
    assert plan.lcl[m] < plan.center_line[m] < plan.ucl[m]
    assert "resolution time" in plan.response_plan


def test_monitor_check_once_flags_degraded_process():
    from lss_copilot.connectors.file_upload import FileUploadConnector
    from lss_copilot.control.monitor import SPCMonitor

    plan = build_control_plan(_events(cycle_hours=24.0))
    monitor = SPCMonitor(FileUploadConnector(), plan)
    degraded = _events(cycle_hours=80.0)  # process blew up post-improvement
    alerts = monitor.check_once(degraded)
    assert any(a.rule == "beyond_3_sigma" and a.metric == "cycle_time_hours" for a in alerts)
    assert plan.alerts  # recorded on the plan for the dashboard
