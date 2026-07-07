"use client";

import { useState } from "react";
import type { StudentDrilldown } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";
import { ScoreBars } from "./ScoreBars";
import { MilestoneTimeline } from "./MilestoneTimeline";
import { FrameworkBreakdown } from "./FrameworkBreakdown";
import { TraceViewer } from "./TraceViewer";
import { ReviewForm } from "./ReviewForm";

type SessionEntry = StudentDrilldown["sessions"][number];

export function SessionCard({ studentId, entry }: { studentId: string; entry: SessionEntry }) {
  const [expanded, setExpanded] = useState(false);
  const { session, assignment, scores, milestones, messageCount, review } = entry;

  const dimensionItems = scores
    ? (Object.keys(DIMENSION_LABELS) as Array<keyof typeof DIMENSION_LABELS>).map((dim) => ({
        key: dim,
        label: DIMENSION_LABELS[dim],
        value: scores.dimensions[dim],
      }))
    : [];

  return (
    <div className="cos-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="cos-kicker">{assignment.code}</p>
          <h3 className="mt-1 text-base font-semibold text-ink">{assignment.title}</h3>
          <p className="mt-0.5 text-xs text-slate-mid">
            {session.status === "completed" ? "Completed" : "In progress"} · {messageCount} message
            {messageCount === 1 ? "" : "s"}
          </p>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-mid">Independence</p>
            <p className="text-xl font-semibold text-ink">{scores ? scores.independenceIndex : "—"}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-mid">Depth</p>
            <p className="text-xl font-semibold text-ink">{scores ? scores.depthScore.toFixed(1) : "—"}</p>
          </div>
        </div>
      </div>

      {scores ? (
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <ScoreBars items={dimensionItems} />
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-mid">
              Reasoning so far
            </p>
            <MilestoneTimeline milestones={milestones} />
          </div>
        </div>
      ) : (
        <p className="mt-4 text-xs text-slate-mid">This session has not been scored yet.</p>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
        <span
          className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
          style={
            review
              ? { background: "var(--color-teal-soft)", color: "var(--color-teal)" }
              : { background: "var(--color-cream-deep)", color: "var(--color-slate-mid)" }
          }
        >
          {review ? `Reviewed by ${review.reviewerName}` : "Not yet reviewed"}
        </span>
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="text-xs font-medium text-teal hover:underline"
        >
          {expanded ? "Hide full trace & review ↑" : "Open full trace & review →"}
        </button>
      </div>

      {expanded ? (
        <div className="mt-5 space-y-6 border-t border-line pt-5">
          {scores ? (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-mid">
                Framework breakdown
              </p>
              <FrameworkBreakdown frameworks={scores.frameworks} />
            </div>
          ) : null}

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-mid">
              Reasoning trace
            </p>
            <TraceViewer studentId={studentId} sessionId={session.id} />
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-mid">
              Faculty review
            </p>
            <ReviewForm sessionId={session.id} initialReview={review} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
