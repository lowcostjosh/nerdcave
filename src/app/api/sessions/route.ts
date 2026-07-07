import { NextResponse } from "next/server";
import { startSession } from "@/lib/sessions";

// POST /api/sessions { studentId, assignmentId } -> SessionState
// Finds the student's existing session for the assignment or creates one
// (with the tutor's opening message).
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const studentId = body?.studentId as string | undefined;
  const assignmentId = body?.assignmentId as string | undefined;
  if (!studentId || !assignmentId) {
    return NextResponse.json({ error: "studentId and assignmentId are required" }, { status: 400 });
  }
  try {
    return NextResponse.json(startSession(studentId, assignmentId));
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 400 });
  }
}
