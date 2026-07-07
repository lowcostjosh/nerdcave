import * as repo from "./repo";
import { openingMessage, runTurn } from "./socratic/engine";
import { computeDimensions, computeDepthScore, computeFrameworks } from "./scoring/frameworks";
import { computeIndependence } from "./scoring/independence";
import type {
  ChatMessage,
  Milestone,
  MilestoneKind,
  QuickAction,
  SessionScores,
  SessionState,
} from "./types";

// Session orchestration: the write path that ties the Socratic engine, the
// reasoning trace, and the scoring layer together.

export function getSessionState(sessionId: string): SessionState | null {
  const session = repo.getSession(sessionId);
  if (!session) return null;
  const student = repo.getStudent(session.studentId);
  const assignment = repo.getAssignment(session.assignmentId);
  if (!student || !assignment) return null;
  return {
    session,
    student,
    assignment,
    messages: repo.listMessages(sessionId),
    milestones: repo.listMilestones(sessionId),
    scores: repo.getScores(sessionId),
  };
}

/** Find or create the student's session for an assignment, with the tutor's opening message. */
export function startSession(studentId: string, assignmentId: string): SessionState {
  const existing = repo.findSession(studentId, assignmentId);
  if (existing) {
    const state = getSessionState(existing.id);
    if (state) return state;
  }

  const assignment = repo.getAssignment(assignmentId);
  if (!assignment) throw new Error(`Unknown assignment: ${assignmentId}`);
  if (!repo.getStudent(studentId)) throw new Error(`Unknown student: ${studentId}`);

  const session = repo.createSession(studentId, assignmentId);
  const opening = openingMessage(assignment);
  repo.insertMessage({
    sessionId: session.id,
    role: "ai",
    content: opening.message,
    tag: opening.tag,
  });

  const state = getSessionState(session.id);
  if (!state) throw new Error("Failed to load created session");
  return state;
}

export interface PostMessageResult {
  studentMessage: ChatMessage;
  aiMessage: ChatMessage;
  newMilestone: Milestone | null;
  scores: SessionScores;
  engine: "claude" | "demo";
}

/** The main turn loop: store the student message, run the engine, persist everything, rescore. */
export async function postStudentMessage(
  sessionId: string,
  content: string,
  quickAction: QuickAction | null
): Promise<PostMessageResult> {
  const session = repo.getSession(sessionId);
  if (!session) throw new Error(`Unknown session: ${sessionId}`);
  if (session.status === "completed") throw new Error("Session is completed");
  const assignment = repo.getAssignment(session.assignmentId);
  if (!assignment) throw new Error("Assignment missing for session");

  const history = repo.listMessages(sessionId);
  const existingMilestoneKinds = new Set<MilestoneKind>(
    repo.listMilestones(sessionId).map((m) => m.kind)
  );

  const studentMessage = repo.insertMessage({
    sessionId,
    role: "student",
    content,
    quickAction,
  });

  const turn = await runTurn({
    assignment,
    history,
    studentText: content,
    quickAction,
    existingMilestoneKinds,
  });

  repo.insertAnalysis({
    messageId: studentMessage.id,
    sessionId,
    moves: turn.analysis.moves,
    challengeResponse: turn.analysis.challengeResponse,
  });

  const aiMessage = repo.insertMessage({
    sessionId,
    role: "ai",
    content: turn.reply.message,
    tag: turn.reply.tag,
  });

  const newMilestone = turn.milestone
    ? repo.insertMilestone({ sessionId, ...turn.milestone })
    : null;

  const scores = recomputeScores(sessionId);

  return { studentMessage, aiMessage, newMilestone, scores, engine: turn.engine };
}

export function recomputeScores(sessionId: string): SessionScores {
  const analyses = repo.listAnalyses(sessionId);
  const messages = repo.listMessages(sessionId);
  const dimensions = computeDimensions(analyses);
  const frameworks = computeFrameworks(analyses);
  const { index, components } = computeIndependence(analyses, messages);
  return repo.upsertScores({
    sessionId,
    dimensions,
    frameworks,
    independenceIndex: index,
    independenceComponents: components,
    depthScore: computeDepthScore(dimensions),
  });
}

export function finishSession(sessionId: string): SessionState {
  const session = repo.getSession(sessionId);
  if (!session) throw new Error(`Unknown session: ${sessionId}`);
  if (session.status !== "completed") {
    recomputeScores(sessionId);
    repo.completeSession(sessionId);
  }
  const state = getSessionState(sessionId);
  if (!state) throw new Error("Failed to load session");
  return state;
}
