"""Blind-recovery check: plant two root causes in messy realistic data and
verify the deterministic pipeline (intake -> mining -> features -> stats)
finds exactly them — no LLM anywhere.

Planted truth:
  RC1: team 'platform' waits ~5x longer in triage.
  RC2: 'billing' component gets reopened 40% of the time.
  Distractor: priority has no effect and must NOT be flagged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lss_copilot.agents.data_intake import DataIntakeAgent
from lss_copilot.agents.statistical_engine import PlannedTest, StatisticalEngineAgent
from lss_copilot.connectors.file_upload import FileUploadConnector
from lss_copilot.mining import case_feature_table, mine_process
from lss_copilot.state.schemas import LSSProjectState
from lss_copilot.tools.artifact_store import ArtifactStore


@pytest.fixture(scope="module")
def messy_csv(tmp_path_factory):
    rng = np.random.default_rng(2026)
    rows = []
    base = pd.Timestamp("2026-03-01")
    for i in range(300):
        team = rng.choice(["web", "platform", "mobile"])
        component = rng.choice(["billing", "auth", "search", "ui"])
        t = base + pd.Timedelta(hours=float(rng.uniform(0, 24 * 60)))
        triage = rng.lognormal(1.0, 0.4) * (5.0 if team == "platform" else 1.0)  # RC1
        fix = rng.lognormal(1.5, 0.5)
        reopen = rng.random() < (0.40 if component == "billing" else 0.05)  # RC2
        seq = [("Created", 0.0), ("Triage", 0.1), ("In Progress", 0.1 + triage),
               ("Review", 0.1 + triage + fix)]
        if reopen:
            seq += [("Reopened", seq[-1][1] + 0.5), ("In Progress", seq[-1][1] + 1.0),
                    ("Review", seq[-1][1] + 1.0 + fix * 0.6)]
        seq += [("Done", seq[-1][1] + 0.5)]
        for act, offset in seq:
            rows.append({
                "Ticket ID": f"TCK-{i}", "Status": act,  # spaces + title case on purpose
                "Updated At": (t + pd.Timedelta(hours=offset)).isoformat(),
                "Team": team, "Component": component,
                "Priority": rng.choice(["P1", "P2", "P3"]),
            })
    rows += rows[:20]  # duplicates
    rows.append({"Ticket ID": "TCK-X", "Status": "Created",  # single-event case
                 "Updated At": base.isoformat(), "Team": "web",
                 "Component": "ui", "Priority": "P3"})
    path = tmp_path_factory.mktemp("data") / "messy.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_intake_normalizes_messy_headers_and_timestamps(messy_csv):
    conn = FileUploadConnector()
    events = conn.to_event_log(conn.fetch(path=messy_csv))
    assert {"case_id", "activity", "timestamp"} <= set(events.columns)
    assert str(events["timestamp"].dtype).startswith("datetime64")
    cleaned = DataIntakeAgent._clean(events)
    assert "TCK-X" not in set(cleaned["case_id"])  # single-event case dropped
    assert not cleaned.duplicated(["case_id", "activity", "timestamp"]).any()


def test_planted_root_causes_recovered(messy_csv, tmp_path):
    conn = FileUploadConnector()
    events = DataIntakeAgent._clean(conn.to_event_log(conn.fetch(path=messy_csv)))

    # MEASURE: triage wait must surface as the top bottleneck
    model = mine_process(events)
    assert model.bottlenecks[0] == ("Triage", "In Progress")

    # ANALYZE: engine on the auto-built feature table
    store = ArtifactStore(tmp_path)
    fref = store.put_dataframe(case_feature_table(events), "upload", "features")
    engine = StatisticalEngineAgent(store)
    state = LSSProjectState(project_id="p", raw_problem_description="slow tickets")
    env = engine.run(state, brief="", dataset=fref, plan=[
        PlannedTest(kind="hypothesis", target_metric="cycle_hours", group_by="Team"),
        PlannedTest(kind="hypothesis", target_metric="cycle_hours", group_by="Priority"),
        PlannedTest(kind="regression", target_metric="cycle_hours",
                    factors=["Team", "reworked"]),
        PlannedTest(kind="hypothesis", target_metric="n_revisits", group_by="Component"),
    ])
    team_test, prio_test, ols, rework_test = env.payload.root

    assert team_test.significant                     # RC1 via hypothesis test
    coefs = ols.details["coefficients"]              # RC1 via one-hot OLS
    platform = next(v for k, v in coefs.items() if "platform" in k)
    assert platform["coef"] > 5 and platform["p_value"] < 1e-6
    assert rework_test.significant                   # RC2: billing rework
    assert not prio_test.significant                 # distractor stays quiet
