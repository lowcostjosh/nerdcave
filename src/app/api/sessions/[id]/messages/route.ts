import { NextResponse } from "next/server";
import { postStudentMessage } from "@/lib/sessions";
import type { QuickAction } from "@/lib/types";

// POST /api/sessions/:id/messages { content, quickAction? } -> PostMessageResult
// The main turn loop: stores the student message, runs the Socratic engine,
// persists the analysis + milestone, and returns updated live scores.
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json().catch(() => null);
  const content = (body?.content as string | undefined)?.trim();
  const quickAction = (body?.quickAction ?? null) as QuickAction | null;
  if (!content) {
    return NextResponse.json({ error: "content is required" }, { status: 400 });
  }
  try {
    const result = await postStudentMessage(id, content, quickAction);
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 400 });
  }
}
