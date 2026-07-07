import type { Milestone } from "@/lib/types";
import { formatTime } from "./constants";

interface MilestoneTimelineProps {
  milestones: Milestone[];
  emptyHint?: string;
}

// Newest-first vertical timeline. Relies on React's keyed reconciliation: an
// item only mounts (and therefore only plays its entrance animation) the
// first time its id appears, so re-renders of existing milestones stay put.
export function MilestoneTimeline({ milestones, emptyHint }: MilestoneTimelineProps) {
  if (milestones.length === 0) {
    return (
      <p className="text-sm italic text-slate-mid">
        {emptyHint ?? "Milestones will appear here as your reasoning develops."}
      </p>
    );
  }

  return (
    <>
      <style>{`
        @keyframes cos-milestone-in {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <ol className="space-y-5">
        {milestones.map((m) => (
          <li
            key={m.id}
            style={{ animation: "cos-milestone-in 0.45s ease-out" }}
            className="relative border-l-2 border-line pl-4"
          >
            <span
              className="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-gold"
              aria-hidden
            />
            <p className="text-sm font-semibold text-ink">{m.label}</p>
            <p className="mt-0.5 text-xs italic leading-relaxed text-ink-soft">{m.detail}</p>
            <p className="mt-1 text-[0.7rem] text-slate-mid">{formatTime(m.createdAt)}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
