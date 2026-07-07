import { NextResponse } from "next/server";
import * as repo from "@/lib/repo";
import { hasClaude } from "@/lib/socratic/engine";

// Everything the client shells need on load: courses, assignments, the
// student roster (demo login), and whether the live AI engine is available.
export async function GET() {
  return NextResponse.json({
    courses: repo.listCourses(),
    assignments: repo.listAssignments(),
    students: repo.listStudents(),
    engine: hasClaude() ? "claude" : "demo",
  });
}
