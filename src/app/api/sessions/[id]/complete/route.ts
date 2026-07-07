import { NextResponse } from "next/server";
import { finishSession } from "@/lib/sessions";

// POST /api/sessions/:id/complete -> SessionState (final scores)
export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    return NextResponse.json(finishSession(id));
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 400 });
  }
}
