import type { Database } from "better-sqlite3";
import { newId } from "./db";
import * as repo from "./repo";
import type {
  Assignment,
  ChatMessage,
  DimensionScores,
  MilestoneKind,
  QuickAction,
  SocraticTag,
} from "./types";
import { heuristicAnalyze, heuristicMilestone, heuristicOpening, heuristicReply } from "./socratic/heuristics";
import { computeDepthScore, computeDimensions, computeFrameworks } from "./scoring/frameworks";
import { computeIndependence } from "./scoring/independence";

import { rngFor, Rng } from "./seed-data/rng";
import { ASSIGNMENTS, COURSE, SKIP_A3_INDICES, STUDENTS, studentEmail } from "./seed-data/students";
import type { Persona } from "./seed-data/students";
import {
  ASSIGNMENT_CONTENT,
  ACCEPT_BARE_PHRASES,
  ADAPT_PHRASES,
  BONUS_PARTNER,
  DEFEND_PHRASES,
  IGNORE_PHRASES,
  REVIEW_COMMENTS,
  type AssignmentContent,
  type ContentCategory,
} from "./seed-data/content";
import {
  CATEGORY_ACTION,
  CHALLENGE_TAGS,
  PERSONA_PROFILES,
  categoryForTag,
  type ChallengeStance,
  type Tier,
} from "./seed-data/personas";

// Deterministic demo-cohort seed for CognitiveOS.
//
// Generates one course, three assignments, 40 students, and a full set of
// completed Socratic tutoring sessions with realistic multi-turn transcripts.
// Every transcript is run through the REAL heuristic engine
// (heuristicAnalyze / heuristicMilestone / heuristicReply) so the resulting
// scores are exactly what the live app would have produced from that text —
// nothing here hand-computes a score. Content selection and all numeric
// choices (dates, tiers, chip usage, review noise) come from a seeded PRNG
// (src/lib/seed-data/rng.ts) — no Math.random, no Date.now().

export function seedDatabase(db: Database): void {
  const courseId = newId("course");
  db.prepare("INSERT INTO courses (id, code, title, term) VALUES (?, ?, ?, ?)").run(
    courseId,
    COURSE.code,
    COURSE.title,
    COURSE.term
  );

  const assignments: Assignment[] = ASSIGNMENTS.map((a) => {
    const id = newId("asgn");
    db.prepare(
      "INSERT INTO assignments (id, course_id, code, title, prompt, due_date) VALUES (?, ?, ?, ?, ?, ?)"
    ).run(id, courseId, a.code, a.title, a.prompt, a.dueDate);
    return { id, courseId, code: a.code, title: a.title, prompt: a.prompt, dueDate: a.dueDate };
  });

  const studentIds: string[] = STUDENTS.map((def, index) => {
    const id = newId("stu");
    const email = studentEmail(def.firstName, def.lastName, index);
    db.prepare("INSERT INTO students (id, name, email, cohort) VALUES (?, ?, ?, ?)").run(
      id,
      `${def.firstName} ${def.lastName}`,
      email,
      "MBA 2026"
    );
    return id;
  });

  // Every student does A1 + A2; ~30/40 have started/completed A3.
  const sessionIdByKey = new Map<string, string>();
  for (let studentIndex = 0; studentIndex < STUDENTS.length; studentIndex++) {
    const def = STUDENTS[studentIndex];
    const studentId = studentIds[studentIndex];
    for (let assignmentIdx = 0; assignmentIdx < assignments.length; assignmentIdx++) {
      if (assignmentIdx === 2 && SKIP_A3_INDICES.has(studentIndex)) continue;
      const sessionId = runSession(db, {
        studentId,
        studentIndex,
        persona: def.persona,
        assignment: assignments[assignmentIdx],
        assignmentIdx,
      });
      sessionIdByKey.set(`${studentIndex}-${assignmentIdx}`, sessionId);
    }
  }

  // Faculty reviews: the first student of each of the 6 persona archetypes,
  // across all 3 assignments they completed -> 18 reviews.
  const reviewStudentIndices = firstOccurrencePerPersona();
  for (const studentIndex of reviewStudentIndices) {
    const persona = STUDENTS[studentIndex].persona;
    for (let assignmentIdx = 0; assignmentIdx < assignments.length; assignmentIdx++) {
      const sessionId = sessionIdByKey.get(`${studentIndex}-${assignmentIdx}`);
      if (!sessionId) continue;
      addFacultyReview({
        studentIndex,
        assignmentIdx,
        sessionId,
        persona,
        assignment: assignments[assignmentIdx],
      });
    }
  }
}

// ---------- Roster helpers ----------

function firstOccurrencePerPersona(): number[] {
  const seen = new Set<Persona>();
  const result: number[] = [];
  STUDENTS.forEach((s, i) => {
    if (!seen.has(s.persona)) {
      seen.add(s.persona);
      result.push(i);
    }
  });
  return result;
}

function sessionStart(assignmentIdx: number, studentIndex: number): Date {
  const due = new Date(`${ASSIGNMENTS[assignmentIdx].dueDate}T00:00:00.000Z`);
  const rng = rngFor("start", studentIndex, assignmentIdx);
  const offsetDays = rng.int(1, 9);
  const hour = rng.int(9, 21);
  const minute = rng.int(0, 59);
  const d = new Date(due.getTime() - offsetDays * 86_400_000);
  d.setUTCHours(hour, minute, 0, 0);
  return d;
}

// ---------- Transcript generation ----------

/**
 * Picks from `arr` via `rng`, retrying a few times to avoid repeating
 * whatever was last picked for this `key` within the session. Content banks
 * are small (a handful of variants each), and reasonAddon/specificAddon in
 * particular get reused almost every turn, so without this a session can
 * visibly repeat the same closer sentence turn after turn.
 */
function pickFresh(rng: Rng, arr: readonly string[], key: string, recent: Map<string, string>): string {
  if (arr.length <= 1) return rng.pick(arr);
  let choice = rng.pick(arr);
  for (let i = 0; i < 4 && choice === recent.get(key); i++) choice = rng.pick(arr);
  recent.set(key, choice);
  return choice;
}

function composeMessage(params: {
  content: AssignmentContent;
  category: "open" | ContentCategory;
  tier: Tier;
  includeBonus: boolean;
  stance: ChallengeStance | null;
  rng: Rng;
  recent: Map<string, string>;
}): string {
  const { content, category, tier, includeBonus, stance, rng, recent } = params;
  const effectiveTier: Tier = category === "assumption" && tier === "high" ? "mid" : tier;

  const coreOf = (cat: "open" | ContentCategory, t: Tier): string =>
    cat === "open"
      ? pickFresh(rng, t === "low" ? content.openPlain : content.openRich, `open.${t}`, recent)
      : pickFresh(rng, content.core[cat], `core.${cat}`, recent);

  const parts: string[] = [coreOf(category, effectiveTier)];
  if (effectiveTier !== "low") parts.push(pickFresh(rng, content.reasonAddon, "reasonAddon", recent));
  if (effectiveTier === "high") parts.push(pickFresh(rng, content.specificAddon, "specificAddon", recent));
  if (category === "reflection" && effectiveTier !== "low") {
    parts.push(pickFresh(rng, content.revision, "revision", recent));
  }
  if (includeBonus && category !== "assumption") {
    const partner = BONUS_PARTNER[category];
    parts.push(coreOf(partner, "low"));
  }

  if (stance === "accept_bare") return [pickFresh(rng, ACCEPT_BARE_PHRASES, "acceptBare", recent), ...parts].join(" ");
  if (stance === "defend") parts.push(pickFresh(rng, DEFEND_PHRASES, "defend", recent));
  else if (stance === "adapt") parts.push(pickFresh(rng, ADAPT_PHRASES, "adapt", recent));
  else if (stance === "ignore") parts.push(pickFresh(rng, IGNORE_PHRASES, "ignore", recent));

  return parts.join(" ");
}

function runSession(
  db: Database,
  params: {
    studentId: string;
    studentIndex: number;
    persona: Persona;
    assignment: Assignment;
    assignmentIdx: number;
  }
): string {
  const { studentId, studentIndex, persona, assignment, assignmentIdx } = params;
  const profile = PERSONA_PROFILES[persona][assignmentIdx];
  const content = ASSIGNMENT_CONTENT[assignmentIdx];
  const rng = rngFor("session", studentIndex, assignmentIdx);

  const turnCount = profile.turnCount;
  const totalMessages = 1 + 2 * turnCount;
  const gaps = totalMessages - 1;
  const start = sessionStart(assignmentIdx, studentIndex);
  const totalSeconds = rng.int(35, 70) * 60;
  const offsets: number[] = [];
  for (let i = 0; i < totalMessages; i++) {
    let t = Math.round((i / gaps) * totalSeconds);
    if (i > 0 && t <= offsets[i - 1]) t = offsets[i - 1] + 1;
    offsets.push(t);
  }
  const isoAt = (i: number) => new Date(start.getTime() + offsets[i] * 1000).toISOString();

  const sessionId = newId("sess");
  db.prepare(
    "INSERT INTO sessions (id, student_id, assignment_id, status, started_at, ended_at) VALUES (?, ?, ?, 'completed', ?, ?)"
  ).run(sessionId, studentId, assignment.id, isoAt(0), isoAt(totalMessages - 1));

  const recent = new Map<string, string>();
  const history: ChatMessage[] = [];
  const opening = heuristicOpening(assignment);
  history.push(
    repo.insertMessage({ sessionId, role: "ai", content: opening.message, tag: opening.tag, createdAt: isoAt(0) })
  );

  let prevAiTag: SocraticTag = opening.tag;
  const existingKinds = new Set<MilestoneKind>();
  let msgIdx = 1;
  // Using a quick-action chip forces heuristicReply's *next* tag deterministically
  // (e.g. test_assumption -> next AI tag is always "assumption_test"), which maps
  // right back to the same content category next turn. Without a cap, a high
  // chipRate can trap a whole session cycling one capped-tier category (e.g.
  // "assumption") instead of progressing, starving every other dimension. Real
  // students wouldn't spam the same scaffold chip every turn either, so allow at
  // most one chip use per category per session.
  const chippedCategories = new Set<ContentCategory | "open">();

  for (let turn = 0; turn < turnCount; turn++) {
    // heuristicReply's natural tag progression rarely reaches "synthesis_check"
    // or "reflection" within a 6-10 turn session (both require 6-7+ *prior*
    // student turns before they're even eligible). Rather than leaving most
    // sessions with zero reflection content, every session deliberately closes
    // with a stock-taking beat: second-to-last turn synthesizes, last turn
    // reflects — mirroring how a real Socratic dialogue naturally winds down,
    // and it's unprompted (prevAiTag usually isn't synthesis_check/reflection),
    // which also helps these turns register as student-originated.
    let forcedCategory: ContentCategory | null = null;
    if (turnCount >= 3) {
      if (turn === turnCount - 2) forcedCategory = "synthesis";
      else if (turn === turnCount - 1) forcedCategory = "reflection";
    }
    const category: "open" | ContentCategory =
      turn === 0 ? "open" : forcedCategory ?? categoryForTag(prevAiTag);

    let tier: Tier;
    if (category === "assumption") {
      const aRng = rngFor("assumption-tier", studentIndex, assignmentIdx, turn);
      tier = aRng.chance(0.2) ? "mid" : "low";
    } else {
      tier = profile.tier;
    }

    const isChallenge = category !== "open" && CHALLENGE_TAGS.includes(prevAiTag);
    const stance: ChallengeStance | null = isChallenge ? profile.challengeStance : null;
    const includeBonus = profile.bonusRigor && category !== "assumption" && rng.chance(0.5);

    const action = category === "open" || chippedCategories.has(category) ? null : CATEGORY_ACTION[category];
    const quickAction: QuickAction | null = action && rng.chance(profile.chipRate) ? action : null;
    if (quickAction) chippedCategories.add(category);

    const text = composeMessage({ content, category, tier, includeBonus, stance, rng, recent });

    const historySoFar = history.slice();
    const analysis = heuristicAnalyze(text, prevAiTag, quickAction);
    const studentCreatedAt = isoAt(msgIdx);
    const studentMsg = repo.insertMessage({
      sessionId,
      role: "student",
      content: text,
      quickAction,
      createdAt: studentCreatedAt,
    });
    repo.insertAnalysis({
      messageId: studentMsg.id,
      sessionId,
      moves: analysis.moves,
      challengeResponse: analysis.challengeResponse,
    });

    const milestone = heuristicMilestone(analysis, text, existingKinds);
    if (milestone) {
      repo.insertMilestone({
        sessionId,
        kind: milestone.kind,
        label: milestone.label,
        detail: milestone.detail,
        createdAt: studentCreatedAt,
      });
      existingKinds.add(milestone.kind);
    }
    msgIdx++;

    const reply = heuristicReply(assignment, historySoFar, analysis, quickAction, text);
    const aiCreatedAt = isoAt(msgIdx);
    const aiMsg = repo.insertMessage({
      sessionId,
      role: "ai",
      content: reply.message,
      tag: reply.tag,
      createdAt: aiCreatedAt,
    });
    msgIdx++;

    history.push(studentMsg, aiMsg);
    prevAiTag = reply.tag;
  }

  const analyses = repo.listAnalyses(sessionId);
  const messages = repo.listMessages(sessionId);
  const dimensions = computeDimensions(analyses);
  const frameworks = computeFrameworks(analyses);
  const depthScore = computeDepthScore(dimensions);
  const { index: independenceIndex, components: independenceComponents } = computeIndependence(analyses, messages);
  repo.upsertScores({ sessionId, dimensions, frameworks, independenceIndex, independenceComponents, depthScore });

  return sessionId;
}

// ---------- Faculty reviews ----------

function clamp4(x: number): number {
  return Math.max(0, Math.min(4, x));
}
function roundHalf(x: number): number {
  return Math.round(x * 2) / 2;
}

function addFacultyReview(params: {
  studentIndex: number;
  assignmentIdx: number;
  sessionId: string;
  persona: Persona;
  assignment: Assignment;
}): void {
  const { studentIndex, assignmentIdx, sessionId, persona, assignment } = params;
  const scores = repo.getScores(sessionId);
  if (!scores) return;
  const rng = rngFor("review", studentIndex, assignmentIdx);
  const noisy = (v: number) => roundHalf(clamp4(v + (rng.next() - 0.5)));
  const dimensions: DimensionScores = {
    evidence_integration: noisy(scores.dimensions.evidence_integration),
    assumption_testing: noisy(scores.dimensions.assumption_testing),
    counterargument_use: noisy(scores.dimensions.counterargument_use),
    reflection_depth: noisy(scores.dimensions.reflection_depth),
  };
  repo.upsertReview({
    sessionId,
    reviewerName: "Dr. S. Stockley",
    dimensions,
    comments: REVIEW_COMMENTS[persona](assignment.title),
  });
}
