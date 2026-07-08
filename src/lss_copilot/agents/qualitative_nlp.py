"""D. Interview & Qualitative NLP Agent (MEDIUM tier).

Turns transcripts / complaints / interview notes into structured Ishikawa
diagrams and FMEA rows. The LLM proposes severity/occurrence/detection scores
from the evidence, but RPN itself is a computed field on `FMEAEntry` — the
model cannot emit an inconsistent RPN. It also drafts the DEFINE-phase
charter when delegated by the orchestrator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from lss_copilot.config import ModelTier
from lss_copilot.agents.base import SubAgent
from lss_copilot.state.schemas import (
    AgentName,
    DMAICPhase,
    FishboneDiagram,
    FMEAEntry,
    HandoffEnvelope,
    LSSProjectState,
    ProjectCharter,
)


class QualitativeAnalysis(BaseModel):
    fishbone: FishboneDiagram
    fmea: list[FMEAEntry] = Field(default_factory=list)
    friction_to_bottleneck_map: dict[str, str] = Field(
        default_factory=dict,
        description="qualitative complaint -> quantitative bottleneck it corroborates",
    )


class QualitativeNLPAgent(SubAgent):
    name = AgentName.QUALITATIVE_NLP
    tier = ModelTier.MEDIUM
    system_prompt = (
        "You are a Six Sigma qualitative analyst. You extract failure modes, "
        "causes, and effects from interviews and complaints, organize causes "
        "into 6M fishbone categories, and score FMEA severity/occurrence/"
        "detection 1-10 with justification grounded in the quoted evidence. "
        "Where measured bottlenecks are provided, map each qualitative "
        "friction to the bottleneck it corroborates."
    )

    def draft_charter(self, state: LSSProjectState) -> HandoffEnvelope:
        """DEFINE: rough problem description -> formal charter + SIPOC."""
        charter, usage = self._ask(
            "Draft a Lean Six Sigma project charter with SIPOC for this problem. "
            "Quantify the problem statement where the text allows; mark unknowns "
            "explicitly rather than inventing figures.\n\n"
            f"Problem description:\n{state.raw_problem_description}",
            ProjectCharter,
        )
        return self._envelope(DMAICPhase.DEFINE, charter, usage, notes="Charter drafted")

    def run(self, state: LSSProjectState, brief: str, transcripts: list[str] | None = None) -> HandoffEnvelope:
        """ANALYZE: transcripts + measured bottlenecks -> fishbone + FMEA."""
        bottlenecks = state.baseline.bottlenecks if state.baseline else []
        corpus = "\n\n---\n\n".join(transcripts or [])
        analysis, usage = self._ask(
            f"Task: {brief}\n"
            f"Measured bottlenecks (from process mining): {bottlenecks}\n"
            f"Effect under study: {state.charter.problem_statement if state.charter else brief}\n\n"
            f"Qualitative inputs:\n{corpus[:60_000]}",  # hard cap on context spend
            QualitativeAnalysis,
        )
        # Rank FMEA by computed RPN before handing off.
        analysis.fmea.sort(key=lambda e: e.rpn, reverse=True)
        return self._envelope(
            DMAICPhase.ANALYZE, analysis, usage,
            notes=f"{len(analysis.fmea)} FMEA rows, top RPN="
                  f"{analysis.fmea[0].rpn if analysis.fmea else 0}",
        )
