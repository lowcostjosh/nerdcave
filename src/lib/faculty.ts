import * as repo from "./repo";
import type {
  CohortFlag,
  DimensionScores,
  DimensionTrend,
  FacultyOverview,
  HeatmapCell,
  ScatterPoint,
  SessionScores,
  StudentDrilldown,
  TrendDirection,
  ValidityStats,
} from "./types";
import { DIMENSION_LABELS } from "./types";

// Faculty analytics: cohort heatmap, trends, independence-vs-depth scatter,
// dependency flags, and convergent-validity stats (platform scores vs faculty
// rubric reviews).

const DIMENSIONS = Object.keys(DIMENSION_LABELS) as Array<keyof DimensionScores>;

interface ScoredSession {
  studentId: string;
  assignmentId: string;
  scores: SessionScores;
}

function scoredSessionsForCourse(courseId: string): ScoredSession[] {
  const assignments = repo.listAssignments(courseId);
  const out: ScoredSession[] = [];
  for (const a of assignments) {
    for (const s of repo.listSessionsForAssignment(a.id)) {
      const scores = repo.getScores(s.id);
      if (scores) out.push({ studentId: s.studentId, assignmentId: a.id, scores });
    }
  }
  return out;
}

export function facultyOverview(courseId: string): FacultyOverview | null {
  const course = repo.getCourse(courseId);
  if (!course) return null;
  const assignments = repo.listAssignments(courseId);
  const sessions = scoredSessionsForCourse(courseId);
  const students = repo.listStudents();
  const studentName = new Map(students.map((s) => [s.id, s.name]));

  // --- Heatmap: mean per dimension x assignment ---
  const heatmap: HeatmapCell[] = [];
  for (const dim of DIMENSIONS) {
    for (const a of assignments) {
      const vals = sessions
        .filter((s) => s.assignmentId === a.id)
        .map((s) => s.scores.dimensions[dim]);
      heatmap.push({
        assignmentId: a.id,
        assignmentCode: a.code,
        dimension: dim,
        mean: vals.length ? round1(vals.reduce((x, y) => x + y, 0) / vals.length) : null,
        sessionCount: vals.length,
      });
    }
  }

  // --- Trends: direction of each dimension across assignments (by code order) ---
  const trends: DimensionTrend[] = DIMENSIONS.map((dim) => {
    const series = assignments
      .map((a) => heatmap.find((c) => c.assignmentId === a.id && c.dimension === dim)?.mean)
      .filter((v): v is number => v !== null && v !== undefined);
    return { dimension: dim, direction: directionOf(series) };
  });

  // --- Scatter: per-student mean independence vs depth ---
  const byStudent = new Map<string, ScoredSession[]>();
  for (const s of sessions) {
    const list = byStudent.get(s.studentId) ?? [];
    list.push(s);
    byStudent.set(s.studentId, list);
  }
  const scatter: ScatterPoint[] = [...byStudent.entries()].map(([studentId, list]) => ({
    studentId,
    studentName: studentName.get(studentId) ?? studentId,
    independence: Math.round(mean(list.map((s) => s.scores.independenceIndex))),
    depth: round1(mean(list.map((s) => s.scores.depthScore))),
    sessionCount: list.length,
  }));

  // --- Flags ---
  const flags = computeFlags(scatter);

  // --- Narrative insight: pick the weakest / most stuck dimension ---
  const insight = buildInsight(trends, heatmap);

  return {
    course,
    assignments,
    heatmap,
    trends,
    scatter,
    flags,
    insight,
    studentCount: byStudent.size,
    sessionCount: sessions.length,
  };
}

const DEPTH_THRESHOLD = 2.4; // out of 4
const INDEPENDENCE_THRESHOLD = 55; // out of 100

function computeFlags(scatter: ScatterPoint[]): CohortFlag[] {
  const flags: CohortFlag[] = [];

  const dependency = scatter.filter(
    (p) => p.depth >= DEPTH_THRESHOLD + 0.4 && p.independence < INDEPENDENCE_THRESHOLD
  );
  if (dependency.length > 0) {
    flags.push({
      id: "dependency_pattern",
      severity: "warning",
      title: `${dependency.length} student${dependency.length === 1 ? "" : "s"} — dependency pattern`,
      description:
        "High depth scores but low independence: strong analytical output that repeatedly requires AI scaffolding to reach. Candidates for an unassisted reasoning exercise.",
      studentIds: dependency.map((p) => p.studentId),
    });
  }

  const belowBoth = scatter.filter(
    (p) => p.depth < DEPTH_THRESHOLD && p.independence < INDEPENDENCE_THRESHOLD
  );
  if (belowBoth.length > 0) {
    flags.push({
      id: "below_both",
      severity: "warning",
      title: `${belowBoth.length} student${belowBoth.length === 1 ? "" : "s"} below both thresholds`,
      description:
        "Below the cohort threshold on both reasoning depth and independence. Recommend targeted intervention before the next assessed assignment.",
      studentIds: belowBoth.map((p) => p.studentId),
    });
  }

  const exemplars = scatter.filter(
    (p) => p.depth >= 3.0 && p.independence >= 75
  );
  if (exemplars.length > 0) {
    flags.push({
      id: "exemplars",
      severity: "info",
      title: `${exemplars.length} student${exemplars.length === 1 ? "" : "s"} — high depth, high independence`,
      description:
        "Strong reasoning produced with minimal scaffolding. Their session traces are candidates for anonymised exemplars in class discussion.",
      studentIds: exemplars.map((p) => p.studentId),
    });
  }

  return flags;
}

function buildInsight(trends: DimensionTrend[], heatmap: HeatmapCell[]): string | null {
  const stuck = trends.find((t) => t.direction === "stuck" || t.direction === "declining");
  if (stuck) {
    const label = DIMENSION_LABELS[stuck.dimension];
    return `${label} is the only dimension not improving — it has barely moved across assignments despite AI prompting. This requires explicit classroom time, not more scaffolding.`;
  }
  const latestByDim = new Map<string, number>();
  for (const cell of heatmap) {
    if (cell.mean !== null) latestByDim.set(cell.dimension, cell.mean);
  }
  if (latestByDim.size === 0) return null;
  const weakest = [...latestByDim.entries()].sort((a, b) => a[1] - b[1])[0];
  return `${DIMENSION_LABELS[weakest[0] as keyof DimensionScores]} is the cohort's weakest dimension (${weakest[1].toFixed(1)}/4.0) — consider making it the focus of the next seminar.`;
}

function directionOf(series: number[]): TrendDirection {
  if (series.length < 2) return "stable";
  const delta = series[series.length - 1] - series[0];
  const lastStep = series[series.length - 1] - series[series.length - 2];
  if (delta >= 0.6) return "improving";
  if (delta >= 0.3) return lastStep >= 0.2 ? "rising" : "improving";
  if (delta <= -0.3) return "declining";
  if (Math.abs(delta) < 0.2 && series[series.length - 1] < 2.2) return "stuck";
  return delta > 0 ? "stable" : "stuck";
}

// ---------- Drilldown ----------

export function studentDrilldown(studentId: string): StudentDrilldown | null {
  const student = repo.getStudent(studentId);
  if (!student) return null;
  const sessions = repo.listSessionsForStudent(studentId).map((session) => {
    const assignment = repo.getAssignment(session.assignmentId)!;
    return {
      session,
      assignment,
      scores: repo.getScores(session.id),
      milestones: repo.listMilestones(session.id),
      messageCount: repo.listMessages(session.id).length,
      review: repo.getReview(session.id),
    };
  });
  return { student, sessions };
}

// ---------- Convergent validity ----------

export function validityStats(): ValidityStats {
  const reviews = repo.listReviews();
  const pairs: Array<{ platform: DimensionScores; faculty: DimensionScores }> = [];
  for (const r of reviews) {
    const scores = repo.getScores(r.sessionId);
    if (scores) pairs.push({ platform: scores.dimensions, faculty: r.dimensions });
  }

  const perDimension = DIMENSIONS.map((dim) => ({
    dimension: dim,
    r: pearson(
      pairs.map((p) => p.platform[dim]),
      pairs.map((p) => p.faculty[dim])
    ),
    n: pairs.length,
  }));

  const overall = {
    r: pearson(
      pairs.map((p) => mean(Object.values(p.platform))),
      pairs.map((p) => mean(Object.values(p.faculty)))
    ),
    n: pairs.length,
  };

  return { perDimension, overall };
}

function pearson(xs: number[], ys: number[]): number | null {
  const n = xs.length;
  if (n < 3) return null;
  const mx = mean(xs);
  const my = mean(ys);
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < n; i++) {
    num += (xs[i] - mx) * (ys[i] - my);
    dx += (xs[i] - mx) ** 2;
    dy += (ys[i] - my) ** 2;
  }
  if (dx === 0 || dy === 0) return null;
  return Math.round((num / Math.sqrt(dx * dy)) * 100) / 100;
}

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

function round1(x: number): number {
  return Math.round(x * 10) / 10;
}
