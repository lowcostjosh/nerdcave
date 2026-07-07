import type {
  Assignment,
  ChatMessage,
  MilestoneKind,
  MoveType,
  QuickAction,
  ReasoningMove,
  SocraticTag,
  TurnAnalysis,
} from "../types";

// Heuristic engine — the zero-API-key fallback.
//
// Provides the same three outputs as the LLM path (reply, move analysis,
// milestone) from deterministic text patterns, so the whole platform runs in
// demo mode without credentials. It is intentionally conservative: pattern
// hits are treated as signals, not proof, and qualities cap lower than the
// LLM analyzer would award.

// ---------- Move detection ----------

interface Pattern {
  type: MoveType;
  regex: RegExp;
}

const PATTERNS: Pattern[] = [
  { type: "assumption_test", regex: /\b(assum\w+|presuppos\w+|taken for granted|depends on whether|only holds if|premise)\b/i },
  { type: "counterargument", regex: /\b(however|on the other hand|counter[- ]?(argument|example|point)|critics|one could argue|objection|push back|challenge to this|skeptic)\b/i },
  { type: "concession", regex: /\b(concede|granted|fair point|you'?re right|i accept|admittedly|that'?s true)\b/i },
  { type: "revision", regex: /\b(i now think|revis\w+|i'?ve changed|updating my|instead,? i|no longer think|i was wrong)\b/i },
  { type: "synthesis", regex: /\b(taken together|overall|in sum|combining|therefore my (thesis|position|view)|putting (this|it) together|my refined)\b/i },
  { type: "reflection", regex: /\b(i realiz\w+|i notice|looking back|my reasoning|i tend to|i was too|reflecting)\b/i },
  { type: "evidence", regex: /\b(for (example|instance)|data|study|studies|research|evidence|\d+(\.\d+)?%|statistics|in the case of|historically|according to)\b/i },
];

const CLAIM_MARKERS = /\b(i (think|believe|argue|contend)|my (view|thesis|position|argument)|should|because|the key (driver|reason|factor)|this (shows|means|suggests))\b/i;

const REASON_MARKERS = /\b(because|since|the reason|given that|due to|which means|this is why)\b/i;

const DISAGREE_MARKERS = /\b(i (still|maintain|disagree|stand by)|but i|even so|nevertheless|my point stands|that doesn'?t)\b/i;

/** Which move type does each AI tag directly elicit? */
const TAG_ELICITS: Partial<Record<SocraticTag, MoveType>> = {
  assumption_test: "assumption_test",
  counterargument: "counterargument",
  evidence_check: "evidence",
  reflection: "reflection",
  synthesis_check: "synthesis",
};

const ACTION_ELICITS: Record<QuickAction, MoveType | null> = {
  unpack_question: null,
  test_assumption: "assumption_test",
  find_counterargument: "counterargument",
  compare_perspectives: null,
  reflect: "reflection",
};

const CHALLENGE_TAGS: SocraticTag[] = [
  "probing",
  "assumption_test",
  "counterargument",
  "evidence_check",
  "perspective_shift",
];

function qualityOf(text: string, matched: boolean): number {
  const hasReasons = REASON_MARKERS.test(text);
  const specific = /\d|for (example|instance)|e\.g\.|such as|[A-Z][a-z]+ (Inc|Corp)|Uber|Airbnb|Visa|Amazon|Tesla|Netflix/i.test(text);
  let q = matched ? 2 : 1;
  if (hasReasons) q += 1;
  if (specific && text.length > 120) q += 1;
  return Math.min(4, q);
}

export function heuristicAnalyze(
  studentText: string,
  prevAiTag: SocraticTag | null,
  quickAction: QuickAction | null
): Omit<TurnAnalysis, "messageId" | "sessionId"> {
  const moves: ReasoningMove[] = [];
  const elicitedType =
    (quickAction ? ACTION_ELICITS[quickAction] : null) ??
    (prevAiTag ? TAG_ELICITS[prevAiTag] ?? null : null);

  for (const p of PATTERNS) {
    if (p.regex.test(studentText)) {
      moves.push({
        type: p.type,
        quality: qualityOf(studentText, true),
        origination: elicitedType === p.type ? "ai_elicited" : "student",
        summary: summarize(studentText, p.type),
      });
    }
  }

  if (CLAIM_MARKERS.test(studentText) || moves.length === 0) {
    moves.push({
      type: "claim",
      quality: qualityOf(studentText, CLAIM_MARKERS.test(studentText)),
      origination: "student",
      summary: summarize(studentText, "claim"),
    });
  }
  if (/\?/.test(studentText)) {
    moves.push({
      type: "question",
      quality: 2,
      origination: "student",
      summary: "Raised a question",
    });
  }

  // Challenge handling
  let challengeResponse: TurnAnalysis["challengeResponse"] = "none";
  if (prevAiTag && CHALLENGE_TAGS.includes(prevAiTag)) {
    const hasReasons = REASON_MARKERS.test(studentText);
    const disagrees = DISAGREE_MARKERS.test(studentText);
    const concedes = moves.some((m) => m.type === "concession" || m.type === "revision");
    if (disagrees && hasReasons) challengeResponse = "defended";
    else if (concedes && hasReasons) challengeResponse = "adapted";
    else if (concedes || /^(yes|true|good point|agreed|ok(ay)?)\b/i.test(studentText.trim()))
      challengeResponse = "accepted_bare";
    else if (hasReasons) challengeResponse = "adapted";
    else challengeResponse = "ignored";
  }

  return { moves, challengeResponse };
}

function summarize(text: string, type: MoveType): string {
  const firstSentence = text.split(/(?<=[.!?])\s+/)[0] ?? text;
  const clipped = firstSentence.length > 90 ? firstSentence.slice(0, 87) + "..." : firstSentence;
  const verbs: Record<MoveType, string> = {
    claim: "Claimed",
    evidence: "Cited evidence",
    assumption_test: "Tested assumption",
    counterargument: "Raised counterargument",
    concession: "Conceded",
    revision: "Revised position",
    synthesis: "Synthesised",
    reflection: "Reflected",
    question: "Asked",
  };
  return `${verbs[type]}: ${clipped}`;
}

// ---------- Milestone detection ----------

export function heuristicMilestone(
  analysis: Omit<TurnAnalysis, "messageId" | "sessionId">,
  studentText: string,
  existingKinds: Set<MilestoneKind>
): { kind: MilestoneKind; label: string; detail: string } | null {
  const has = (t: MoveType, minQ = 0) => analysis.moves.some((m) => m.type === t && m.quality >= minQ);
  const excerpt = studentText.length > 110 ? `“${studentText.slice(0, 107)}...”` : `“${studentText}”`;

  const candidates: Array<{ kind: MilestoneKind; label: string; detail: string; when: boolean }> = [
    {
      kind: "synthesis_reached",
      label: "Synthesis reached",
      detail: `Integrated the threads of the discussion — ${excerpt}`,
      when: has("synthesis", 3),
    },
    {
      kind: "position_defended",
      label: "Position defended",
      detail: "Held their position under challenge with independent reasons.",
      when: analysis.challengeResponse === "defended",
    },
    {
      kind: "counterargument_integrated",
      label: "Counterargument integrated",
      detail: `Engaged the opposing case on its merits — ${excerpt}`,
      when: has("counterargument", 3) || (has("counterargument") && has("concession")),
    },
    {
      kind: "thesis_revised",
      label: "Thesis revised",
      detail: `Updated their position in light of the discussion — ${excerpt}`,
      when: has("revision"),
    },
    {
      kind: "assumption_surfaced",
      label: "Assumption surfaced",
      detail: `Identified a load-bearing premise — ${excerpt}`,
      when: has("assumption_test"),
    },
    {
      kind: "evidence_grounded",
      label: "Evidence grounded",
      detail: `Anchored the argument in specifics — ${excerpt}`,
      when: has("evidence", 3),
    },
    {
      kind: "thesis_formed",
      label: "Thesis crystallised",
      detail: excerpt,
      when: has("claim", 3),
    },
  ];

  for (const c of candidates) {
    if (c.when && !existingKinds.has(c.kind)) return { kind: c.kind, label: c.label, detail: c.detail };
  }
  return null;
}

// ---------- Demo-mode Socratic reply ----------

const OPENERS: Record<SocraticTag, (frag: string, topic: string) => string> = {
  probing: (frag) =>
    `You said ${frag}. What exactly is the mechanism doing the work in that claim? Name the specific cause, not the category it belongs to.`,
  assumption_test: (frag) =>
    `There's an assumption underneath ${frag} — that the conditions which made this true will keep holding. Describe a realistic scenario where that premise fails. Does your position survive it?`,
  counterargument: (frag) =>
    `Take the strongest version of the opposing view to ${frag}: someone who has thought hard about this and disagrees. What is their best single piece of evidence, and how do you reconcile your claim with it?`,
  evidence_check: (frag) =>
    `What evidence would convince a skeptic of ${frag} — and just as importantly, what observation would falsify it? If you can't name the second, the claim isn't yet doing analytical work.`,
  perspective_shift: (frag) =>
    `You've been arguing ${frag} from one vantage point. How does the picture change for a different stakeholder — a regulator, a new entrant, a customer with alternatives? Does your claim hold from there?`,
  synthesis_check: () =>
    `Pause and take stock: state your current position in two sentences, and name the one thing from this discussion that changed it. If nothing changed it, what would have to be true for you to update?`,
  reflection: () =>
    `Step back from the argument to your reasoning about it. Where in this discussion were you most confident — and is that confidence coming from evidence, or from the claim being familiar?`,
  orientation: (_frag, topic) =>
    `Before we build an answer, let's take the question apart. In your own words: what is "${topic}" actually asking you to decide, and what would a strong answer have to demonstrate?`,
};

function fragmentOf(text: string): string {
  const words = text.replace(/\s+/g, " ").trim().split(" ");
  const frag = words.slice(0, 12).join(" ");
  return `“${frag}${words.length > 12 ? "..." : ""}”`;
}

const ACTION_TAGS: Record<QuickAction, SocraticTag> = {
  unpack_question: "probing",
  test_assumption: "assumption_test",
  find_counterargument: "counterargument",
  compare_perspectives: "perspective_shift",
  reflect: "reflection",
};

/**
 * Choose the next Socratic move in demo mode: honour a quick action if used,
 * otherwise pick the move that targets the biggest gap in the trace so far.
 */
export function heuristicReply(
  assignment: Assignment,
  history: ChatMessage[],
  analysis: Omit<TurnAnalysis, "messageId" | "sessionId">,
  quickAction: QuickAction | null,
  studentText: string
): { tag: SocraticTag; message: string } {
  if (quickAction) {
    const tag = ACTION_TAGS[quickAction];
    return { tag, message: OPENERS[tag](fragmentOf(studentText), assignment.title) };
  }

  const usedTags = new Set(history.filter((m) => m.role === "ai" && m.tag).map((m) => m.tag));
  const studentTurns = history.filter((m) => m.role === "student").length;

  const hasMove = (t: MoveType) => analysis.moves.some((m) => m.type === t);

  let tag: SocraticTag;
  if (hasMove("claim") && !hasMove("evidence")) tag = "evidence_check";
  else if (!usedTags.has("assumption_test") && studentTurns >= 2) tag = "assumption_test";
  else if (!usedTags.has("counterargument") && studentTurns >= 3) tag = "counterargument";
  else if (!usedTags.has("perspective_shift") && studentTurns >= 4) tag = "perspective_shift";
  else if (studentTurns >= 6 && !usedTags.has("synthesis_check")) tag = "synthesis_check";
  else if (studentTurns >= 7 && !usedTags.has("reflection")) tag = "reflection";
  else tag = "probing";

  return { tag, message: OPENERS[tag](fragmentOf(studentText), assignment.title) };
}

export function heuristicOpening(assignment: Assignment): { tag: SocraticTag; message: string } {
  return {
    tag: "orientation",
    message: `Welcome — I'm your thinking partner for “${assignment.title}”. I won't give you answers; my job is to make your reasoning sharper and visibly your own. ${OPENERS.orientation("", assignment.title)}`,
  };
}
