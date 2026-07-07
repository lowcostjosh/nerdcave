import { getDb, newId, nowIso } from "./db";
import type {
  Assignment,
  ChatMessage,
  Course,
  DimensionScores,
  FacultyReview,
  FrameworkScores,
  IndependenceComponents,
  Milestone,
  MilestoneKind,
  MessageRole,
  QuickAction,
  ReasoningMove,
  Session,
  SessionScores,
  SocraticTag,
  Student,
  TurnAnalysis,
} from "./types";

// Thin data-access layer: row <-> domain type mapping lives here so the rest
// of the engine works with plain typed objects.

/* eslint-disable @typescript-eslint/no-explicit-any */

function rowToCourse(r: any): Course {
  return { id: r.id, code: r.code, title: r.title, term: r.term };
}
function rowToAssignment(r: any): Assignment {
  return {
    id: r.id,
    courseId: r.course_id,
    code: r.code,
    title: r.title,
    prompt: r.prompt,
    dueDate: r.due_date,
  };
}
function rowToStudent(r: any): Student {
  return { id: r.id, name: r.name, email: r.email, cohort: r.cohort };
}
function rowToSession(r: any): Session {
  return {
    id: r.id,
    studentId: r.student_id,
    assignmentId: r.assignment_id,
    status: r.status,
    startedAt: r.started_at,
    endedAt: r.ended_at,
  };
}
function rowToMessage(r: any): ChatMessage {
  return {
    id: r.id,
    sessionId: r.session_id,
    role: r.role as MessageRole,
    content: r.content,
    tag: (r.tag ?? null) as SocraticTag | null,
    quickAction: (r.quick_action ?? null) as QuickAction | null,
    createdAt: r.created_at,
  };
}
function rowToMilestone(r: any): Milestone {
  return {
    id: r.id,
    sessionId: r.session_id,
    kind: r.kind as MilestoneKind,
    label: r.label,
    detail: r.detail,
    createdAt: r.created_at,
  };
}
function rowToScores(r: any): SessionScores {
  return {
    sessionId: r.session_id,
    dimensions: JSON.parse(r.dimensions_json),
    frameworks: JSON.parse(r.frameworks_json),
    independenceIndex: r.independence_index,
    independenceComponents: JSON.parse(r.independence_components_json),
    depthScore: r.depth_score,
    updatedAt: r.updated_at,
  };
}
function rowToReview(r: any): FacultyReview {
  return {
    sessionId: r.session_id,
    reviewerName: r.reviewer_name,
    dimensions: JSON.parse(r.dimensions_json),
    comments: r.comments,
    createdAt: r.created_at,
  };
}
function rowToAnalysis(r: any): TurnAnalysis {
  return {
    messageId: r.message_id,
    sessionId: r.session_id,
    moves: JSON.parse(r.moves_json),
    challengeResponse: r.challenge_response,
  };
}

// ---------- Reads ----------

export function listCourses(): Course[] {
  return getDb().prepare("SELECT * FROM courses ORDER BY code").all().map(rowToCourse);
}
export function getCourse(id: string): Course | null {
  const r = getDb().prepare("SELECT * FROM courses WHERE id = ?").get(id);
  return r ? rowToCourse(r) : null;
}
export function listAssignments(courseId?: string): Assignment[] {
  const db = getDb();
  const rows = courseId
    ? db.prepare("SELECT * FROM assignments WHERE course_id = ? ORDER BY code").all(courseId)
    : db.prepare("SELECT * FROM assignments ORDER BY code").all();
  return rows.map(rowToAssignment);
}
export function getAssignment(id: string): Assignment | null {
  const r = getDb().prepare("SELECT * FROM assignments WHERE id = ?").get(id);
  return r ? rowToAssignment(r) : null;
}
export function listStudents(): Student[] {
  return getDb().prepare("SELECT * FROM students ORDER BY name").all().map(rowToStudent);
}
export function getStudent(id: string): Student | null {
  const r = getDb().prepare("SELECT * FROM students WHERE id = ?").get(id);
  return r ? rowToStudent(r) : null;
}
export function getSession(id: string): Session | null {
  const r = getDb().prepare("SELECT * FROM sessions WHERE id = ?").get(id);
  return r ? rowToSession(r) : null;
}
export function findSession(studentId: string, assignmentId: string): Session | null {
  const r = getDb()
    .prepare("SELECT * FROM sessions WHERE student_id = ? AND assignment_id = ? ORDER BY started_at DESC LIMIT 1")
    .get(studentId, assignmentId);
  return r ? rowToSession(r) : null;
}
export function listSessionsForStudent(studentId: string): Session[] {
  return getDb()
    .prepare("SELECT * FROM sessions WHERE student_id = ? ORDER BY started_at")
    .all(studentId)
    .map(rowToSession);
}
export function listSessionsForAssignment(assignmentId: string): Session[] {
  return getDb()
    .prepare("SELECT * FROM sessions WHERE assignment_id = ? ORDER BY started_at")
    .all(assignmentId)
    .map(rowToSession);
}
export function listMessages(sessionId: string): ChatMessage[] {
  return getDb()
    .prepare("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at, rowid")
    .all(sessionId)
    .map(rowToMessage);
}
export function listMilestones(sessionId: string): Milestone[] {
  return getDb()
    .prepare("SELECT * FROM milestones WHERE session_id = ? ORDER BY created_at, rowid")
    .all(sessionId)
    .map(rowToMilestone);
}
export function listAnalyses(sessionId: string): TurnAnalysis[] {
  return getDb()
    .prepare(
      `SELECT ta.* FROM turn_analyses ta
       JOIN messages m ON m.id = ta.message_id
       WHERE ta.session_id = ? ORDER BY m.created_at, m.rowid`
    )
    .all(sessionId)
    .map(rowToAnalysis);
}
export function getScores(sessionId: string): SessionScores | null {
  const r = getDb().prepare("SELECT * FROM session_scores WHERE session_id = ?").get(sessionId);
  return r ? rowToScores(r) : null;
}
export function getReview(sessionId: string): FacultyReview | null {
  const r = getDb().prepare("SELECT * FROM faculty_reviews WHERE session_id = ?").get(sessionId);
  return r ? rowToReview(r) : null;
}
export function listReviews(): FacultyReview[] {
  return getDb().prepare("SELECT * FROM faculty_reviews").all().map(rowToReview);
}

// ---------- Writes ----------

export function createSession(studentId: string, assignmentId: string): Session {
  const session: Session = {
    id: newId("sess"),
    studentId,
    assignmentId,
    status: "active",
    startedAt: nowIso(),
    endedAt: null,
  };
  getDb()
    .prepare(
      "INSERT INTO sessions (id, student_id, assignment_id, status, started_at, ended_at) VALUES (?, ?, ?, ?, ?, ?)"
    )
    .run(session.id, session.studentId, session.assignmentId, session.status, session.startedAt, session.endedAt);
  return session;
}

export function completeSession(sessionId: string): void {
  getDb()
    .prepare("UPDATE sessions SET status = 'completed', ended_at = ? WHERE id = ?")
    .run(nowIso(), sessionId);
}

export function insertMessage(msg: {
  sessionId: string;
  role: MessageRole;
  content: string;
  tag?: SocraticTag | null;
  quickAction?: QuickAction | null;
  createdAt?: string;
}): ChatMessage {
  const m: ChatMessage = {
    id: newId("msg"),
    sessionId: msg.sessionId,
    role: msg.role,
    content: msg.content,
    tag: msg.tag ?? null,
    quickAction: msg.quickAction ?? null,
    createdAt: msg.createdAt ?? nowIso(),
  };
  getDb()
    .prepare(
      "INSERT INTO messages (id, session_id, role, content, tag, quick_action, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    .run(m.id, m.sessionId, m.role, m.content, m.tag, m.quickAction, m.createdAt);
  return m;
}

export function insertAnalysis(a: TurnAnalysis): void {
  getDb()
    .prepare(
      "INSERT OR REPLACE INTO turn_analyses (message_id, session_id, moves_json, challenge_response) VALUES (?, ?, ?, ?)"
    )
    .run(a.messageId, a.sessionId, JSON.stringify(a.moves), a.challengeResponse);
}

export function insertMilestone(m: {
  sessionId: string;
  kind: MilestoneKind;
  label: string;
  detail: string;
  createdAt?: string;
}): Milestone {
  const milestone: Milestone = {
    id: newId("mile"),
    sessionId: m.sessionId,
    kind: m.kind,
    label: m.label,
    detail: m.detail,
    createdAt: m.createdAt ?? nowIso(),
  };
  getDb()
    .prepare("INSERT INTO milestones (id, session_id, kind, label, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)")
    .run(milestone.id, milestone.sessionId, milestone.kind, milestone.label, milestone.detail, milestone.createdAt);
  return milestone;
}

export function upsertScores(s: {
  sessionId: string;
  dimensions: DimensionScores;
  frameworks: FrameworkScores;
  independenceIndex: number;
  independenceComponents: IndependenceComponents;
  depthScore: number;
}): SessionScores {
  const updatedAt = nowIso();
  getDb()
    .prepare(
      `INSERT OR REPLACE INTO session_scores
       (session_id, dimensions_json, frameworks_json, independence_index, independence_components_json, depth_score, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      s.sessionId,
      JSON.stringify(s.dimensions),
      JSON.stringify(s.frameworks),
      s.independenceIndex,
      JSON.stringify(s.independenceComponents),
      s.depthScore,
      updatedAt
    );
  return { ...s, updatedAt };
}

export function upsertReview(r: {
  sessionId: string;
  reviewerName: string;
  dimensions: DimensionScores;
  comments: string;
}): FacultyReview {
  const createdAt = nowIso();
  getDb()
    .prepare(
      `INSERT OR REPLACE INTO faculty_reviews (session_id, reviewer_name, dimensions_json, comments, created_at)
       VALUES (?, ?, ?, ?, ?)`
    )
    .run(r.sessionId, r.reviewerName, JSON.stringify(r.dimensions), r.comments, createdAt);
  return { ...r, createdAt };
}

/** Export a raw move list helper used by scoring */
export type { ReasoningMove };
