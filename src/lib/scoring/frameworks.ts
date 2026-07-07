import type {
  AacuScores,
  BloomScores,
  DimensionScores,
  FrameworkScores,
  MoveType,
  PaulElderScores,
  ReasoningMove,
  TurnAnalysis,
} from "../types";

// Multi-framework scoring layer.
//
// Turn analyses tag each student message with reasoning moves (type, quality
// 0-4, origination). This module aggregates those moves into:
//   1. the four cohort dimensions shown in the professor heatmap, and
//   2. per-framework breakdowns (AAC&U VALUE rubric, Paul-Elder standards,
//      Bloom's taxonomy).
//
// Aggregation is deterministic given the move tags, so the same trace always
// produces the same score regardless of whether tagging came from the LLM
// analyzer or the heuristic fallback.

function clamp4(x: number): number {
  return Math.max(0, Math.min(4, x));
}

function round1(x: number): number {
  return Math.round(x * 10) / 10;
}

/**
 * Quality-weighted mean of moves of the given types, with a coverage ramp:
 * one weak move shouldn't score like a sustained pattern, so scores ramp up
 * toward the quality mean as move count approaches `fullCredit`.
 */
function dimensionScore(moves: ReasoningMove[], types: MoveType[], fullCredit = 3): number {
  const relevant = moves.filter((m) => types.includes(m.type));
  if (relevant.length === 0) return 0;
  const meanQuality = relevant.reduce((s, m) => s + m.quality, 0) / relevant.length;
  const coverage = Math.min(1, relevant.length / fullCredit);
  return clamp4(meanQuality * (0.5 + 0.5 * coverage));
}

export function computeDimensions(analyses: TurnAnalysis[]): DimensionScores {
  const moves = analyses.flatMap((a) => a.moves);
  return {
    evidence_integration: round1(dimensionScore(moves, ["evidence", "synthesis"])),
    assumption_testing: round1(dimensionScore(moves, ["assumption_test"])),
    counterargument_use: round1(dimensionScore(moves, ["counterargument", "concession"])),
    reflection_depth: round1(dimensionScore(moves, ["reflection", "revision"])),
  };
}

export function computeFrameworks(analyses: TurnAnalysis[]): FrameworkScores {
  const moves = analyses.flatMap((a) => a.moves);

  const aacu: AacuScores = {
    explanation_of_issues: round1(dimensionScore(moves, ["claim", "question"], 2)),
    evidence: round1(dimensionScore(moves, ["evidence"])),
    influence_of_context_assumptions: round1(dimensionScore(moves, ["assumption_test"])),
    students_position: round1(dimensionScore(moves, ["claim", "counterargument", "concession"])),
    conclusions_outcomes: round1(dimensionScore(moves, ["synthesis", "revision"], 2)),
  };

  const paulElder: PaulElderScores = {
    clarity: round1(dimensionScore(moves, ["claim", "question"], 2)),
    accuracy: round1(dimensionScore(moves, ["evidence"])),
    depth: round1(dimensionScore(moves, ["assumption_test", "synthesis"])),
    breadth: round1(dimensionScore(moves, ["counterargument", "concession"], 2)),
    logic: round1(dimensionScore(moves, ["claim", "evidence", "synthesis"], 4)),
    fairness: round1(dimensionScore(moves, ["concession", "counterargument", "reflection"])),
  };

  const bloom: BloomScores = {
    understand: round1(dimensionScore(moves, ["claim", "question"], 2)),
    apply: round1(dimensionScore(moves, ["evidence"], 2)),
    analyze: round1(dimensionScore(moves, ["assumption_test", "counterargument"])),
    evaluate: round1(dimensionScore(moves, ["concession", "revision", "reflection"])),
    create: round1(dimensionScore(moves, ["synthesis"], 2)),
  };

  return { aacu, paulElder, bloom };
}

export function computeDepthScore(dimensions: DimensionScores): number {
  const vals = Object.values(dimensions);
  return round1(vals.reduce((s, v) => s + v, 0) / vals.length);
}
