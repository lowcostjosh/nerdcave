import { NextResponse } from "next/server";
import { validityStats } from "@/lib/faculty";

// GET /api/faculty/validity -> ValidityStats
// Convergent validity: Pearson r between platform dimension scores and
// faculty rubric reviews across all reviewed sessions.
export async function GET() {
  return NextResponse.json(validityStats());
}
