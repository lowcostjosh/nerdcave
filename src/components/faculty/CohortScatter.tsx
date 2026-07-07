"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { CohortFlag, ScatterPoint } from "@/lib/types";
import { SCATTER_CATEGORY_COLOR, SCATTER_CATEGORY_LABEL, type ScatterCategory } from "./colors";

const WIDTH = 640;
const HEIGHT = 380;
const MARGIN = { top: 28, right: 24, bottom: 48, left: 52 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;
const X_THRESHOLD = 55;
const Y_THRESHOLD = 2.4;

function xScale(independence: number) {
  return MARGIN.left + (Math.min(100, Math.max(0, independence)) / 100) * PLOT_W;
}
function yScale(depth: number) {
  return MARGIN.top + (1 - Math.min(4, Math.max(0, depth)) / 4) * PLOT_H;
}

function categoryFor(studentId: string, flags: CohortFlag[]): ScatterCategory {
  const dependency = flags.find((f) => f.id === "dependency_pattern");
  if (dependency?.studentIds.includes(studentId)) return "dependency";
  const belowBoth = flags.find((f) => f.id === "below_both");
  if (belowBoth?.studentIds.includes(studentId)) return "belowBoth";
  const exemplars = flags.find((f) => f.id === "exemplars");
  if (exemplars?.studentIds.includes(studentId)) return "exemplar";
  return "other";
}

export function CohortScatter({ scatter, flags }: { scatter: ScatterPoint[]; flags: CohortFlag[] }) {
  const router = useRouter();
  const [hovered, setHovered] = useState<ScatterPoint | null>(null);

  const points = useMemo(
    () => scatter.map((p) => ({ ...p, category: categoryFor(p.studentId, flags) })),
    [scatter, flags]
  );

  const xTicks = [0, 25, 50, 75, 100];
  const yTicks = [0, 1, 2, 3, 4];

  const legendCategories: ScatterCategory[] = ["exemplar", "dependency", "belowBoth", "other"];

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4">
        {legendCategories.map((cat) => (
          <span key={cat} className="inline-flex items-center gap-1.5 text-xs text-ink-soft">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: SCATTER_CATEGORY_COLOR[cat], opacity: cat === "other" ? 0.6 : 1 }}
            />
            {SCATTER_CATEGORY_LABEL[cat]}
          </span>
        ))}
      </div>

      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full min-w-[480px]"
          role="img"
          aria-label="Scatter plot of independence index versus reasoning depth, one dot per student"
          onMouseLeave={() => setHovered(null)}
        >
          {/* gridlines */}
          {xTicks.map((t) => (
            <line
              key={`gx-${t}`}
              x1={xScale(t)}
              x2={xScale(t)}
              y1={MARGIN.top}
              y2={HEIGHT - MARGIN.bottom}
              stroke="var(--color-line)"
              strokeWidth={1}
            />
          ))}
          {yTicks.map((t) => (
            <line
              key={`gy-${t}`}
              x1={MARGIN.left}
              x2={WIDTH - MARGIN.right}
              y1={yScale(t)}
              y2={yScale(t)}
              stroke="var(--color-line)"
              strokeWidth={1}
            />
          ))}

          {/* threshold guides */}
          <line
            x1={xScale(X_THRESHOLD)}
            x2={xScale(X_THRESHOLD)}
            y1={MARGIN.top}
            y2={HEIGHT - MARGIN.bottom}
            stroke="var(--color-slate-mid)"
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.6}
          />
          <line
            x1={MARGIN.left}
            x2={WIDTH - MARGIN.right}
            y1={yScale(Y_THRESHOLD)}
            y2={yScale(Y_THRESHOLD)}
            stroke="var(--color-slate-mid)"
            strokeWidth={1}
            strokeDasharray="4 3"
            opacity={0.6}
          />

          {/* axes */}
          <line
            x1={MARGIN.left}
            x2={WIDTH - MARGIN.right}
            y1={HEIGHT - MARGIN.bottom}
            y2={HEIGHT - MARGIN.bottom}
            stroke="var(--color-slate-mid)"
            strokeWidth={1}
          />
          <line
            x1={MARGIN.left}
            x2={MARGIN.left}
            y1={MARGIN.top}
            y2={HEIGHT - MARGIN.bottom}
            stroke="var(--color-slate-mid)"
            strokeWidth={1}
          />
          {xTicks.map((t) => (
            <text
              key={`xt-${t}`}
              x={xScale(t)}
              y={HEIGHT - MARGIN.bottom + 18}
              textAnchor="middle"
              className="fill-slate-mid"
              fontSize={11}
            >
              {t}
            </text>
          ))}
          {yTicks.map((t) => (
            <text
              key={`yt-${t}`}
              x={MARGIN.left - 10}
              y={yScale(t) + 4}
              textAnchor="end"
              className="fill-slate-mid"
              fontSize={11}
            >
              {t}
            </text>
          ))}
          <text
            x={MARGIN.left + PLOT_W / 2}
            y={HEIGHT - 6}
            textAnchor="middle"
            className="fill-ink-soft"
            fontSize={12}
          >
            Independence Index (0–100)
          </text>
          <text
            x={-(MARGIN.top + PLOT_H / 2)}
            y={14}
            textAnchor="middle"
            transform="rotate(-90)"
            className="fill-ink-soft"
            fontSize={12}
          >
            Depth score (0–4)
          </text>

          {/* quadrant hints */}
          <text
            x={MARGIN.left + 8}
            y={MARGIN.top + 14}
            className="fill-slate-mid italic"
            fontSize={10.5}
          >
            high depth, low independence
          </text>
          <text
            x={WIDTH - MARGIN.right - 8}
            y={MARGIN.top + 14}
            textAnchor="end"
            className="fill-slate-mid italic"
            fontSize={10.5}
          >
            high depth, high independence
          </text>

          {/* dots */}
          {points.map((p) => {
            const cx = xScale(p.independence);
            const cy = yScale(p.depth);
            const color = SCATTER_CATEGORY_COLOR[p.category];
            const opacity = p.category === "other" ? 0.6 : 1;
            const isHovered = hovered?.studentId === p.studentId;
            return (
              <g
                key={p.studentId}
                tabIndex={0}
                role="link"
                aria-label={`${p.studentName}: independence ${p.independence}, depth ${p.depth.toFixed(1)}. Open drilldown.`}
                className="cursor-pointer outline-none"
                onMouseEnter={() => setHovered(p)}
                onFocus={() => setHovered(p)}
                onBlur={() => setHovered((cur) => (cur?.studentId === p.studentId ? null : cur))}
                onClick={() => router.push(`/faculty/students/${p.studentId}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    router.push(`/faculty/students/${p.studentId}`);
                  }
                }}
              >
                {/* larger transparent hit target */}
                <circle cx={cx} cy={cy} r={13} fill="transparent" />
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 7 : 5.5}
                  fill={color}
                  opacity={opacity}
                  stroke="var(--color-card)"
                  strokeWidth={2}
                  style={{ transition: "r 100ms ease" }}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {hovered ? (
        <div className="mt-2 inline-flex items-center gap-2 rounded-md border border-line bg-cream-deep px-3 py-1.5 text-xs">
          <span className="font-semibold text-ink">{hovered.studentName}</span>
          <span className="text-ink-soft">
            Independence {hovered.independence} · Depth {hovered.depth.toFixed(1)} ·{" "}
            {hovered.sessionCount} session{hovered.sessionCount === 1 ? "" : "s"}
          </span>
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-mid">Hover or focus a dot for details · click to open the student.</p>
      )}
    </div>
  );
}
