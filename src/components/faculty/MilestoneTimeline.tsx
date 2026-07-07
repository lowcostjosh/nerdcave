import type { Milestone } from "@/lib/types";

export function MilestoneTimeline({ milestones }: { milestones: Milestone[] }) {
  if (milestones.length === 0) {
    return <p className="text-xs text-slate-mid">No milestones recorded for this session yet.</p>;
  }
  const sorted = [...milestones].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );
  return (
    <ol className="space-y-3 border-l border-line pl-4">
      {sorted.map((m) => (
        <li key={m.id} className="relative">
          <span
            className="absolute -left-[1.15rem] top-1 h-2 w-2 rounded-full"
            style={{ background: "var(--color-gold)" }}
          />
          <p className="text-sm font-medium text-ink">{m.label}</p>
          <p className="text-xs leading-relaxed text-ink-soft">{m.detail}</p>
          <p className="mt-0.5 text-[11px] text-slate-mid">
            {new Date(m.createdAt).toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </li>
      ))}
    </ol>
  );
}
