// Shared domain types for CognitiveOS.
// These are the contracts between the engine (src/lib), API routes, and both UIs.

// ---------- Entities ----------

export interface Course {
  id: string;
  code: string;
  title: string;
  term: string;
}

export interface Assignment {
  id: string;
  courseId: string;
  /** Short code shown in the heatmap columns, e.g. "A1" */
  code: string;
  title: string;
  /** The essay/analysis prompt students are reasoning about */
  prompt: string;
  dueDate: string; // ISO date
}

export interface Student {
  id: string;
  name: string;
  email: string;
  cohort: string;
}

export type SessionStatus = "active" | "completed";

export interface Session {
  id: string;
  studentId: string;
  assignmentId: string;
  status: SessionStatus;
  startedAt: string; // ISO datetime
  endedAt: string | null;
}

export type MessageRole = "student" | "ai";

/** Tag shown on AI messages describing the Socratic move being made */
export type SocraticTag =
  | "probing"
  | "assumption_test"
  | "counterargument"
  | "evidence_check"
  | "perspective_shift"
  | "synthesis_check"
  | "reflection"
  | "orientation";

/** Quick-action chips available in the student composer */
export type QuickAction =
  | "unpack_question"
  | "test_assumption"
  | "find_counterargument"
  | "compare_perspectives"
  | "reflect";

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  /** Set on AI messages */
  tag: SocraticTag | null;
  /** Set on student messages sent via a quick-action chip */
  quickAction: QuickAction | null;
  createdAt: string;
}

// ---------- Reasoning trace ----------

/** The kinds of reasoning moves we detect in student messages */
export type MoveType =
  | "claim"
  | "evidence"
  | "assumption_test"
  | "counterargument"
  | "concession"
  | "revision"
  | "synthesis"
  | "reflection"
  | "question";

export interface ReasoningMove {
  type: MoveType;
  /** 0-4 quality of the move */
  quality: number;
  /**
   * Did the student originate this move, or was it directly elicited by the
   * AI's immediately preceding prompt (e.g. AI asked for a counterargument
   * and the student supplied one)?
   */
  origination: "student" | "ai_elicited";
  /** One-line summary of the move, used in the trace viewer */
  summary: string;
}

export interface TurnAnalysis {
  messageId: string;
  sessionId: string;
  moves: ReasoningMove[];
  /**
   * How the student handled the AI's most recent challenge, when there was
   * one: defended with reasons, adapted the position with reasons, accepted
   * without reasons, or ignored it.
   */
  challengeResponse: "defended" | "adapted" | "accepted_bare" | "ignored" | "none";
}

/** Milestone shown in the "Reasoning so far" sidebar */
export type MilestoneKind =
  | "thesis_formed"
  | "thesis_revised"
  | "claim_compounded"
  | "assumption_surfaced"
  | "counterargument_integrated"
  | "evidence_grounded"
  | "position_defended"
  | "synthesis_reached";

export interface Milestone {
  id: string;
  sessionId: string;
  kind: MilestoneKind;
  /** Short headline, e.g. "Thesis crystallised" */
  label: string;
  /** One-two line detail, e.g. the claim itself */
  detail: string;
  createdAt: string;
}

// ---------- Scoring ----------

/** The four cohort-level reasoning dimensions (0-4 each) */
export interface DimensionScores {
  evidence_integration: number;
  assumption_testing: number;
  counterargument_use: number;
  reflection_depth: number;
}

export const DIMENSION_LABELS: Record<keyof DimensionScores, string> = {
  evidence_integration: "Evidence integration",
  assumption_testing: "Assumption testing",
  counterargument_use: "Counterargument use",
  reflection_depth: "Reflection depth",
};

/** AAC&U Critical Thinking VALUE rubric criteria (0-4) */
export interface AacuScores {
  explanation_of_issues: number;
  evidence: number;
  influence_of_context_assumptions: number;
  students_position: number;
  conclusions_outcomes: number;
}

/** Paul-Elder intellectual standards applied to elements of thought (0-4) */
export interface PaulElderScores {
  clarity: number;
  accuracy: number;
  depth: number;
  breadth: number;
  logic: number;
  fairness: number;
}

/** Bloom's taxonomy — evidence of activity at each level (0-4) */
export interface BloomScores {
  understand: number;
  apply: number;
  analyze: number;
  evaluate: number;
  create: number;
}

export interface FrameworkScores {
  aacu: AacuScores;
  paulElder: PaulElderScores;
  bloom: BloomScores;
}

/** Components of the Independence Index, each 0-1 */
export interface IndependenceComponents {
  /** Share of substantive moves the student originated unprompted */
  origination: number;
  /** Rigour moves (evidence / assumption tests / counterarguments) offered without being asked */
  unpromptedRigor: number;
  /** Quality of responses when the AI challenged the student */
  challengeResponse: number;
  /** Inverse reliance on quick-action scaffolds */
  scaffoldIndependence: number;
}

export interface SessionScores {
  sessionId: string;
  dimensions: DimensionScores;
  frameworks: FrameworkScores;
  /** 0-100 */
  independenceIndex: number;
  independenceComponents: IndependenceComponents;
  /** Mean of the four dimensions, 0-4 — the "depth" axis of the scatter */
  depthScore: number;
  updatedAt: string;
}

/** Faculty rubric assessment of the same session — the convergent-validity pair */
export interface FacultyReview {
  sessionId: string;
  reviewerName: string;
  /** Faculty's 0-4 rating on the same four dimensions */
  dimensions: DimensionScores;
  comments: string;
  createdAt: string;
}

// ---------- API view models ----------

export interface SessionState {
  session: Session;
  student: Student;
  assignment: Assignment;
  messages: ChatMessage[];
  milestones: Milestone[];
  scores: SessionScores | null;
}

/** One cell of the faculty heatmap */
export interface HeatmapCell {
  assignmentId: string;
  assignmentCode: string;
  dimension: keyof DimensionScores;
  /** Cohort mean 0-4, null when no data */
  mean: number | null;
  sessionCount: number;
}

export type TrendDirection = "improving" | "rising" | "stable" | "stuck" | "declining";

export interface DimensionTrend {
  dimension: keyof DimensionScores;
  direction: TrendDirection;
}

export interface ScatterPoint {
  studentId: string;
  studentName: string;
  /** 0-100 */
  independence: number;
  /** 0-4 */
  depth: number;
  sessionCount: number;
}

export interface CohortFlag {
  id: string;
  severity: "warning" | "info";
  title: string;
  description: string;
  studentIds: string[];
}

export interface FacultyOverview {
  course: Course;
  assignments: Assignment[];
  heatmap: HeatmapCell[];
  trends: DimensionTrend[];
  scatter: ScatterPoint[];
  flags: CohortFlag[];
  insight: string | null;
  studentCount: number;
  sessionCount: number;
}

export interface StudentDrilldown {
  student: Student;
  sessions: Array<{
    session: Session;
    assignment: Assignment;
    scores: SessionScores | null;
    milestones: Milestone[];
    messageCount: number;
    review: FacultyReview | null;
  }>;
}

export interface ValidityStats {
  /** Pearson r between platform depth score and faculty mean rubric, per dimension */
  perDimension: Array<{
    dimension: keyof DimensionScores;
    r: number | null;
    n: number;
  }>;
  overall: { r: number | null; n: number };
}
