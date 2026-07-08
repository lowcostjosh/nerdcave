import pandas as pd

from lss_copilot.mining import case_feature_table, mine_process


def _log() -> pd.DataFrame:
    base = pd.Timestamp("2026-02-01", tz="UTC")
    rows = [
        # straight-through case, team A
        {"case_id": "A1", "activity": "Created", "timestamp": base, "team": "a"},
        {"case_id": "A1", "activity": "Fix", "timestamp": base + pd.Timedelta(hours=4), "team": "a"},
        {"case_id": "A1", "activity": "Done", "timestamp": base + pd.Timedelta(hours=10), "team": "a"},
        # rework case via intermediate state, team B
        {"case_id": "B1", "activity": "Created", "timestamp": base, "team": "b"},
        {"case_id": "B1", "activity": "Fix", "timestamp": base + pd.Timedelta(hours=1), "team": "b"},
        {"case_id": "B1", "activity": "Review", "timestamp": base + pd.Timedelta(hours=2), "team": "b"},
        {"case_id": "B1", "activity": "Fix", "timestamp": base + pd.Timedelta(hours=3), "team": "b"},
        {"case_id": "B1", "activity": "Done", "timestamp": base + pd.Timedelta(hours=6), "team": "b"},
    ]
    return pd.DataFrame(rows)


def test_feature_table_rolls_up_cases():
    features = case_feature_table(_log()).set_index("case_id")
    assert features.loc["A1", "cycle_hours"] == 10.0
    assert features.loc["B1", "cycle_hours"] == 6.0
    assert features.loc["A1", "n_revisits"] == 0
    assert features.loc["B1", "n_revisits"] == 1  # Fix visited twice
    assert bool(features.loc["B1", "reworked"]) is True
    assert features.loc["A1", "team"] == "a"  # attribute carried through
    # dwell: A1 spends 4h in Created, 6h in Fix
    assert features.loc["A1", "hours_in_created"] == 4.0
    assert features.loc["A1", "hours_in_fix"] == 6.0


def test_revisit_loop_through_intermediate_state_detected():
    model = mine_process(_log())
    # Review -> Fix closes a loop even though Fix -> Review -> Fix passes
    # through an intermediate state (the old A->B->A rule missed this).
    assert ("Review", "Fix") in model.rework_loops


def test_mermaid_sanitizes_hostile_labels():
    df = _log().replace({"Fix": 'Fix "quick" <hack>'})
    model = mine_process(df)
    mermaid = model.to_mermaid()
    assert '"quick"' not in mermaid and "<hack>" not in mermaid
    assert "Fix 'quick' (hack)" in mermaid
