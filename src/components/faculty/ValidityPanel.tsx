import { DIMENSION_LABELS } from "@/lib/types";
import type { ValidityStats } from "@/lib/types";
import { validityBarColor } from "./colors";

function RBar({ label, r, n }: { label: string; r: number | null; n: number }) {
  const pct = r === null ? 0 : Math.min(100, Math.abs(r) * 50);
  return (
    <div className="grid grid-cols-[9rem_1fr_5rem] items-center gap-3 text-sm">
      <span className="truncate text-ink-soft">{label}</span>
      <span className="relative h-4 rounded-sm" style={{ background: "var(--color-cream-deep)" }}>
        {/* zero midpoint */}
        <span
          className="absolute inset-y-0 left-1/2 w-px"
          style={{ background: "var(--color-slate-mid)" }}
        />
        {r !== null ? (
          <span
            className="absolute inset-y-0 rounded-sm"
            style={
              r >= 0
                ? { left: "50%", width: `${pct}%`, background: validityBarColor(r) }
                : { right: "50%", width: `${pct}%`, background: validityBarColor(r) }
            }
          />
        ) : null}
      </span>
      <span className="text-right font-mono text-xs tabular-nums text-ink">
        {r === null ? "needs ≥3 reviews" : `r = ${r.toFixed(2)}`}
      </span>
    </div>
  );
}

export function ValidityPanel({ stats }: { stats: ValidityStats }) {
  return (
    <div className="cos-card p-5">
      <p className="cos-kicker">Convergent validity</p>
      <h3 className="mt-1 text-base font-semibold text-ink">
        Platform score vs faculty rubric
      </h3>
      <p className="mt-1 text-xs text-slate-mid">
        Pearson r between the platform&apos;s dimension score and the faculty rubric review for the
        same session, across every reviewed session (n = {stats.overall.n}).
      </p>

      <div className="mt-4 space-y-2.5">
        {stats.perDimension.map((d) => (
          <RBar key={d.dimension} label={DIMENSION_LABELS[d.dimension]} r={d.r} n={d.n} />
        ))}
      </div>

      <div className="mt-4 border-t border-line pt-3">
        <RBar label="Overall" r={stats.overall.r} n={stats.overall.n} />
      </div>

      {stats.overall.r === null ? (
        <p className="mt-3 text-xs text-slate-mid">
          Correlations need at least 3 faculty reviews before they&apos;re computed. Submit reviews
          from a student drilldown to build this out.
        </p>
      ) : null}
    </div>
  );
}
