import type { QuickAction, SocraticTag } from "../types";
import type { ContentCategory } from "./content";
import type { Persona } from "./students";

// Per-persona, per-assignment behavioral profile driving transcript
// generation. `tier` controls message quality (heuristicAnalyze reads
// pattern-match + reason-marker + specific/length off the whole message);
// `chipRate` controls quick-action reliance; `bonusRigor` controls whether a
// student volunteers an extra, unprompted rigor sentence of a different move
// type in the same turn (the main lever for the Independence Index, since
// heuristicAnalyze marks a move "ai_elicited" only when it matches the type
// the AI's preceding tag/action was fishing for); `challengeStance` decides
// how the student responds whenever the AI's preceding tag was a challenge.

export type Tier = "low" | "mid" | "high";
export type ChallengeStance = "defend" | "adapt" | "accept_bare" | "ignore";

export interface PersonaProfile {
  tier: Tier;
  chipRate: number;
  bonusRigor: boolean;
  challengeStance: ChallengeStance;
  turnCount: number;
}

type ProfileTable = Record<Persona, [PersonaProfile, PersonaProfile, PersonaProfile]>;

export const PERSONA_PROFILES: ProfileTable = {
  "independent-strong": [
    { tier: "mid", chipRate: 0.05, bonusRigor: true, challengeStance: "defend", turnCount: 7 },
    { tier: "mid", chipRate: 0.05, bonusRigor: true, challengeStance: "defend", turnCount: 8 },
    { tier: "high", chipRate: 0.05, bonusRigor: true, challengeStance: "defend", turnCount: 9 },
  ],
  "scaffolded-achiever": [
    // Good content, but leans on scaffolds and rarely pushes back independently
    // when challenged (accept_bare rather than adapt/defend) — the dependency
    // pattern: high depth, low independence.
    { tier: "high", chipRate: 0.85, bonusRigor: false, challengeStance: "accept_bare", turnCount: 8 },
    { tier: "high", chipRate: 0.9, bonusRigor: false, challengeStance: "accept_bare", turnCount: 8 },
    { tier: "high", chipRate: 0.95, bonusRigor: false, challengeStance: "accept_bare", turnCount: 8 },
  ],
  developing: [
    { tier: "low", chipRate: 0.1, bonusRigor: false, challengeStance: "accept_bare", turnCount: 6 },
    { tier: "low", chipRate: 0.1, bonusRigor: false, challengeStance: "accept_bare", turnCount: 6 },
    { tier: "low", chipRate: 0.1, bonusRigor: false, challengeStance: "accept_bare", turnCount: 6 },
  ],
  improver: [
    { tier: "low", chipRate: 0.3, bonusRigor: false, challengeStance: "accept_bare", turnCount: 6 },
    { tier: "mid", chipRate: 0.2, bonusRigor: false, challengeStance: "adapt", turnCount: 7 },
    { tier: "high", chipRate: 0.08, bonusRigor: true, challengeStance: "defend", turnCount: 9 },
  ],
  contrarian: [
    { tier: "mid", chipRate: 0.15, bonusRigor: true, challengeStance: "defend", turnCount: 7 },
    { tier: "mid", chipRate: 0.15, bonusRigor: true, challengeStance: "defend", turnCount: 8 },
    { tier: "high", chipRate: 0.15, bonusRigor: true, challengeStance: "defend", turnCount: 8 },
  ],
  "steady-mid": [
    { tier: "mid", chipRate: 0.2, bonusRigor: false, challengeStance: "adapt", turnCount: 6 },
    { tier: "mid", chipRate: 0.2, bonusRigor: false, challengeStance: "adapt", turnCount: 7 },
    { tier: "mid", chipRate: 0.2, bonusRigor: false, challengeStance: "adapt", turnCount: 8 },
  ],
};

/** Mirrors heuristics.ts's private CHALLENGE_TAGS list (not exported there). */
export const CHALLENGE_TAGS: SocraticTag[] = [
  "probing",
  "assumption_test",
  "counterargument",
  "evidence_check",
  "perspective_shift",
];

/** Maps the AI's preceding tag to the content category the student responds with. */
export function categoryForTag(tag: SocraticTag): ContentCategory {
  switch (tag) {
    case "evidence_check":
      return "evidence";
    case "assumption_test":
      return "assumption";
    case "counterargument":
      return "counter";
    case "perspective_shift":
      return "perspective";
    case "synthesis_check":
      return "synthesis";
    case "reflection":
      return "reflection";
    case "probing":
    case "orientation":
    default:
      return "evidence";
  }
}

/** Quick-action chip a student would plausibly reach for to produce this category of response. */
export const CATEGORY_ACTION: Record<ContentCategory, QuickAction | null> = {
  evidence: "unpack_question",
  assumption: "test_assumption",
  counter: "find_counterargument",
  perspective: "compare_perspectives",
  synthesis: null,
  reflection: "reflect",
};
