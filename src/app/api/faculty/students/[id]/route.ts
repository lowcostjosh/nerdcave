import { NextResponse } from "next/server";
import { studentDrilldown } from "@/lib/faculty";
import * as repo from "@/lib/repo";

// GET /api/faculty/students/:id -> StudentDrilldown (+ full trace per session
// via ?sessionId= to fetch messages/analyses for the trace viewer)
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("sessionId");

  if (sessionId) {
    return NextResponse.json({
      messages: repo.listMessages(sessionId),
      analyses: repo.listAnalyses(sessionId),
      milestones: repo.listMilestones(sessionId),
      scores: repo.getScores(sessionId),
    });
  }

  const drilldown = studentDrilldown(id);
  if (!drilldown) return NextResponse.json({ error: "Student not found" }, { status: 404 });
  return NextResponse.json(drilldown);
}
