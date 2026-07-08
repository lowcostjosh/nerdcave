import pandas as pd
import pytest

from lss_copilot.mining import mine_process, process_cycle_efficiency


def _event_log() -> pd.DataFrame:
    rows = []
    base = pd.Timestamp("2026-01-05", tz="UTC")
    for i in range(10):
        t = base + pd.Timedelta(days=i)
        rows += [
            {"case_id": f"C{i}", "activity": "Created", "timestamp": t},
            {"case_id": f"C{i}", "activity": "Triage", "timestamp": t + pd.Timedelta(hours=2)},
            {"case_id": f"C{i}", "activity": "Fix", "timestamp": t + pd.Timedelta(hours=30)},
            {"case_id": f"C{i}", "activity": "Done", "timestamp": t + pd.Timedelta(hours=32)},
        ]
    # one rework loop
    rows += [
        {"case_id": "C99", "activity": "Created", "timestamp": base},
        {"case_id": "C99", "activity": "Fix", "timestamp": base + pd.Timedelta(hours=1)},
        {"case_id": "C99", "activity": "Reopened", "timestamp": base + pd.Timedelta(hours=2)},
        {"case_id": "C99", "activity": "Fix", "timestamp": base + pd.Timedelta(hours=3)},
        {"case_id": "C99", "activity": "Done", "timestamp": base + pd.Timedelta(hours=4)},
    ]
    return pd.DataFrame(rows)


def test_mine_process_finds_bottleneck_and_loops():
    model = mine_process(_event_log())
    assert ("Triage", "Fix") in model.bottlenecks  # 28h transition dominates
    assert ("Fix", "Reopened") in model.rework_loops or ("Reopened", "Fix") in model.rework_loops
    assert model.mean_cycle_time_hours == pytest.approx((32 * 10 + 4) / 11, rel=1e-6)
    assert len(model.variants) == 2


def test_mermaid_output_contains_nodes_and_edges():
    model = mine_process(_event_log())
    mermaid = model.to_mermaid()
    assert mermaid.startswith("flowchart LR")
    assert '"Triage"' in mermaid
    assert "-->" in mermaid


def test_missing_columns_rejected():
    with pytest.raises(ValueError, match="missing columns"):
        mine_process(pd.DataFrame({"case_id": [], "activity": []}))


def test_pce():
    assert process_cycle_efficiency(2, 10) == 0.2
    assert process_cycle_efficiency(15, 10) == 1.0  # clamped
    with pytest.raises(ValueError):
        process_cycle_efficiency(1, 0)
