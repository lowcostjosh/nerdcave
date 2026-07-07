import { NextResponse } from "next/server";
import { getSessionState } from "@/lib/sessions";

// GET /api/sessions/:id -> SessionState
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const state = getSessionState(id);
  if (!state) return NextResponse.json({ error: "Session not found" }, { status: 404 });
  return NextResponse.json(state);
}
