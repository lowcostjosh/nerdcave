import { NextResponse } from "next/server";
import * as repo from "@/lib/repo";
import type { DimensionScores } from "@/lib/types";

// POST /api/faculty/reviews { sessionId, reviewerName, dimensions, comments }
// Faculty rubric assessment of a session — the other half of the
// convergent-validity design.
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const sessionId = body?.sessionId as string | undefined;
  const dimensions = body?.dimensions as DimensionScores | undefined;
  if (!sessionId || !dimensions) {
    return NextResponse.json({ error: "sessionId and dimensions are required" }, { status: 400 });
  }
  if (!repo.getSession(sessionId)) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 });
  }
  const review = repo.upsertReview({
    sessionId,
    reviewerName: (body?.reviewerName as string) || "Faculty",
    dimensions,
    comments: (body?.comments as string) || "",
  });
  return NextResponse.json(review);
}
