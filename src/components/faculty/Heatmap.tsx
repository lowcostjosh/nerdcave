"use client";

import type { Assignment, DimensionScores, DimensionTrend, HeatmapCell } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";
import { heatmapCellColor, trendChipStyle } from "./colors";
import { Chip } from "./Chip";

const DIMENSIONS = Object.keys(DIMENSION_LABELS) as Array<keyof DimensionScores>;

export function Heatmap({
  assignments,
  heatmap,
  trends,
}: {
  assignments: Assignment[];
  heatmap: HeatmapCell[];
  trends: DimensionTrend[];
}) {
  const cellFor = (dim: keyof DimensionScores, assignmentId: string) =>
    heatmap.find((c) => c.dimension === dim && c.assignmentId === assignmentId) ?? null;
  const trendFor = (dim: keyof DimensionScores) => trends.find((t) => t.dimension === dim) ?? null;

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full min-w-[560px] border-collapse text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-card px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-slate-mid">
                Dimension
              </th>
              {assignments.map((a) => (
                <th
                  key={a.id}
                  className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-slate-mid"
                  title={a.title}
                >
                  {a.code}
                </th>
              ))}
              <th className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-slate-mid">
                Direction
              </th>
            </tr>
          </thead>
          <tbody>
            {DIMENSIONS.map((dim) => {
              const trend = trendFor(dim);
              const chip = trend ? trendChipStyle(trend.direction) : null;
              return (
                <tr key={dim} className="border-t border-line">
                  <td className="sticky left-0 z-10 whitespace-nowrap bg-card px-3 py-2 font-medium text-ink">
                    {DIMENSION_LABELS[dim]}
                  </td>
                  {assignments.map((a) => {
                    const cell = cellFor(dim, a.id);
                    const { bg, fg } = heatmapCellColor(cell?.mean ?? null);
                    return (
                      <td key={a.id} className="p-1.5 text-center">
                        <div
                          tabIndex={0}
                          className="group relative mx-auto flex h-11 w-full min-w-[3.5rem] cursor-default items-center justify-center rounded-md text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-ink/40"
                          style={{ background: bg, color: fg }}
                        >
                          {cell?.mean === null || cell?.mean === undefined ? "—" : cell.mean.toFixed(1)}
                          <div
                            className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-[11px] font-normal text-cream opacity-0 shadow-lg transition-opacity duration-100 group-hover:opacity-100 group-focus:opacity-100"
                          >
                            {a.code} · {DIMENSION_LABELS[dim]}: {cell && cell.sessionCount > 0 ? `${cell.sessionCount} session${cell.sessionCount === 1 ? "" : "s"}` : "no data"}
                          </div>
                        </div>
                      </td>
                    );
                  })}
                  <td className="px-1.5 py-2 text-center">
                    {chip ? <Chip label={chip.label} bg={chip.bg} fg={chip.fg} /> : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-mid">
        Rows = reasoning dimensions · Columns = assignments · Scores out of 4.0
      </p>
    </div>
  );
}
