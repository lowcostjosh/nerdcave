import pytest
from pydantic import ValidationError

from lss_copilot.state.schemas import (
    AgentName,
    DMAICPhase,
    FishboneDiagram,
    FMEAEntry,
    HumanGate,
    LSSProjectState,
    RootCause,
    TokenLedger,
)


def test_rpn_is_computed_not_supplied():
    entry = FMEAEntry(
        failure_mode="Ticket stuck in triage", effect="SLA breach", cause="No routing rule",
        severity=8, occurrence=6, detection=4,
    )
    assert entry.rpn == 192
    assert entry.model_dump()["rpn"] == 192


def test_fmea_scores_bounded():
    with pytest.raises(ValidationError):
        FMEAEntry(failure_mode="x", effect="y", cause="z",
                  severity=11, occurrence=1, detection=1)


def test_root_causes_capped_at_top_3_by_confidence():
    causes = [RootCause(description=f"rc{i}", confidence=c)
              for i, c in enumerate([0.2, 0.9, 0.5, 0.7])]
    state = LSSProjectState(project_id="p", raw_problem_description="d", root_causes=causes)
    assert [rc.confidence for rc in state.root_causes] == [0.9, 0.7, 0.5]


def test_gate_approval_lookup():
    state = LSSProjectState(
        project_id="p", raw_problem_description="d",
        gates=[HumanGate(phase=DMAICPhase.DEFINE, approved=True)],
    )
    assert state.gate_approved(DMAICPhase.DEFINE)
    assert not state.gate_approved(DMAICPhase.ANALYZE)


def test_token_ledger_accumulates():
    ledger = TokenLedger()
    ledger.record(AgentName.DATA_INTAKE, 100)
    ledger.record(AgentName.DATA_INTAKE, 50)
    ledger.record(AgentName.ORCHESTRATOR, 900)
    assert ledger.by_agent["data_intake"] == 150
    assert ledger.total == 1050


def test_fishbone_mermaid():
    fb = FishboneDiagram(effect="Slow resolution",
                         causes={"Method": ["No triage SLA"], "Man": []})
    mermaid = fb.to_mermaid()
    assert "mindmap" in mermaid and "Slow resolution" in mermaid and "No triage SLA" in mermaid
    assert "Man" not in mermaid.split("Method")[0]  # empty categories omitted
