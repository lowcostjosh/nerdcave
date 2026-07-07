import { NextResponse } from "next/server";
import * as repo from "@/lib/repo";
import { facultyOverview } from "@/lib/faculty";

// GET /api/faculty/overview?courseId=... -> FacultyOverview
// Defaults to the first course when none specified.
export async function GET(request: Request) {
  const url = new URL(request.url);
  let courseId = url.searchParams.get("courseId");
  if (!courseId) {
    courseId = repo.listCourses()[0]?.id ?? null;
  }
  if (!courseId) return NextResponse.json({ error: "No courses" }, { status: 404 });
  const overview = facultyOverview(courseId);
  if (!overview) return NextResponse.json({ error: "Course not found" }, { status: 404 });
  return NextResponse.json(overview);
}
