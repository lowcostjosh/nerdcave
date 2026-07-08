"""End-to-end DMAIC run against a CSV export, with human tollgates.

Usage:
    export LSS_ANTHROPIC_API_KEY=sk-ant-...
    python examples/run_dmaic.py path/to/events.csv "Ticket resolution takes too long..."
"""

from __future__ import annotations

import json
import sys
import uuid

from langgraph.types import Command

from lss_copilot.agents.data_intake import DataIntakeAgent
from lss_copilot.agents.llm import AnthropicRouter
from lss_copilot.agents.process_mining import ProcessMiningAgent
from lss_copilot.agents.prototyping import PrototypingAgent
from lss_copilot.agents.qualitative_nlp import QualitativeNLPAgent
from lss_copilot.agents.statistical_engine import StatisticalEngineAgent
from lss_copilot.connectors.file_upload import FileUploadConnector
from lss_copilot.orchestrator.graph import Orchestrator, build_graph
from lss_copilot.state.schemas import LSSProjectState
from lss_copilot.tools.artifact_store import ArtifactStore


def main() -> None:
    csv_path, problem = sys.argv[1], sys.argv[2]

    llm = AnthropicRouter()
    store = ArtifactStore()
    connector = FileUploadConnector()

    orchestrator = Orchestrator(
        llm=llm,
        intake=DataIntakeAgent(connector, store, llm=llm),
        mining=ProcessMiningAgent(store, llm=llm),
        stats=StatisticalEngineAgent(store, llm=llm),
        qualitative=QualitativeNLPAgent(llm=llm),
        prototyping=PrototypingAgent(llm=llm),
        intake_query={"path": csv_path},
    )
    app = build_graph(orchestrator)

    state = LSSProjectState(
        project_id=f"lss-{uuid.uuid4().hex[:8]}",
        raw_problem_description=problem,
    )
    config = {"configurable": {"thread_id": state.project_id}}

    result = app.invoke(state, config)
    while "__interrupt__" in result:
        gate = result["__interrupt__"][0].value
        answer = input(f"\n{gate['question']} [y/N] ").strip().lower()
        result = app.invoke(
            Command(resume={"approved": answer == "y", "reviewer": "cli"}), config
        )

    final = LSSProjectState.model_validate(result)
    out = f"{final.project_id}_state.json"
    with open(out, "w") as fh:
        fh.write(json.dumps(final.model_dump(mode="json"), indent=2))
    print(f"\nDone. Phase={final.phase.value}, tokens={final.ledger.total:,}. "
          f"State written to {out} — view with:\n"
          f"  streamlit run src/lss_copilot/dashboard/streamlit_app.py -- --state {out}")


if __name__ == "__main__":
    main()
