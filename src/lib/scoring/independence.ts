import type { ChatMessage, IndependenceComponents, TurnAnalysis } from "../types";

// Independence Index — the platform's novel output.
//
// Measures reasoning *ownership*: how much of the intellectual work in a
// session originated with the student, versus being pulled out of them by the
// AI. Four observable components, each 0-1, combined into a 0-100 index:
//
//   origination (35%)          — share of substantive moves the student made
//                                unprompted rather than in direct response to
//                                an AI elicitation of that move type
//   unpromptedRigor (30%)      — rigour moves (evidence, assumption tests,
//                                counterarguments) volunteered without the AI
//                                asking for them, per student turn
//   challengeResponse (25%)    — when the AI pushed back, did the student
//                                defend or adapt with reasons (high), accept
//                                without reasons (low), or ignore it
//   scaffoldIndependence (10%) — inverse reliance on quick-action chips
//
// The index is deterministic over the reasoning trace, which is what makes it
// auditable: every point can be traced back to specific moves in the
// transcript.

const WEIGHTS: Record<keyof IndependenceComponents, number> = {
  origination: 0.35,
  unpromptedRigor: 0.3,
  challengeResponse: 0.25,
  scaffoldIndependence: 0.1,
};

const RIGOR_TYPES = new Set(["evidence", "assumption_test", "counterargument"]);
const SUBSTANTIVE_TYPES = new Set([
  "claim",
  "evidence",
  "assumption_test",
  "counterargument",
  "synthesis",
  "revision",
]);

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

export function computeIndependence(
  analyses: TurnAnalysis[],
  messages: ChatMessage[]
): { index: number; components: IndependenceComponents } {
  const studentMessages = messages.filter((m) => m.role === "student");
  const moves = analyses.flatMap((a) => a.moves);
  const substantive = moves.filter((m) => SUBSTANTIVE_TYPES.has(m.type));

  // 1. Origination: student-originated share of substantive moves
  const origination =
    substantive.length === 0
      ? 0
      : substantive.filter((m) => m.origination === "student").length / substantive.length;

  // 2. Unprompted rigour: volunteered rigour moves per student turn.
  //    One volunteered rigour move per turn ≈ full marks.
  const volunteeredRigor = moves.filter(
    (m) => RIGOR_TYPES.has(m.type) && m.origination === "student"
  ).length;
  const unpromptedRigor =
    studentMessages.length === 0 ? 0 : clamp01(volunteeredRigor / studentMessages.length);

  // 3. Challenge response: quality of engagement when the AI pushed back
  const challenged = analyses.filter((a) => a.challengeResponse !== "none");
  const challengeScore = (r: TurnAnalysis["challengeResponse"]): number => {
    switch (r) {
      case "defended":
        return 1;
      case "adapted":
        return 0.9;
      case "accepted_bare":
        return 0.3;
      case "ignored":
        return 0.1;
      default:
        return 0;
    }
  };
  const challengeResponse =
    challenged.length === 0
      ? 0.5 // no challenges observed — neutral prior
      : challenged.reduce((s, a) => s + challengeScore(a.challengeResponse), 0) / challenged.length;

  // 4. Scaffold independence: inverse of quick-action chip reliance
  const chipTurns = studentMessages.filter((m) => m.quickAction !== null).length;
  const scaffoldIndependence =
    studentMessages.length === 0 ? 1 : clamp01(1 - chipTurns / studentMessages.length);

  const components: IndependenceComponents = {
    origination: round2(origination),
    unpromptedRigor: round2(unpromptedRigor),
    challengeResponse: round2(challengeResponse),
    scaffoldIndependence: round2(scaffoldIndependence),
  };

  const index = Math.round(
    100 *
      (Object.keys(WEIGHTS) as Array<keyof IndependenceComponents>).reduce(
        (s, k) => s + WEIGHTS[k] * components[k],
        0
      )
  );

  return { index, components };
}

function round2(x: number): number {
  return Math.round(x * 100) / 100;
}
