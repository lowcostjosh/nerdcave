import { DIMENSION_LABELS, type SessionScores } from "@/lib/types";

const DIMENSION_KEYS = Object.keys(DIMENSION_LABELS) as Array<keyof typeof DIMENSION_LABELS>;

export function LiveSignals({ scores }: { scores: SessionScores | null }) {
  if (!scores) {
    return (
      <p className="text-sm italic text-slate-mid">
        Signals will appear after your first exchange.
      </p>
    );
  }

  const index = Math.round(scores.independenceIndex);

  return (
    <div>
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-xs font-medium text-ink-soft">Independence Index</span>
          <span className="text-2xl font-semibold tabular-nums text-ink">{index}</span>
        </div>
        <div
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-cream-deep"
          role="progressbar"
          aria-valuenow={index}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Independence Index"
        >
          <div
            className="h-full rounded-full bg-teal transition-[width] duration-500 ease-out"
            style={{ width: `${Math.min(100, Math.max(0, index))}%` }}
          />
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {DIMENSION_KEYS.map((key) => {
          const value = scores.dimensions[key];
          return (
            <div key={key}>
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-ink-soft">{DIMENSION_LABELS[key]}</span>
                <span className="text-xs tabular-nums text-slate-mid">
                  {value.toFixed(1)} / 4
                </span>
              </div>
              <div className="mt-1 flex gap-1" aria-hidden>
                {Array.from({ length: 4 }).map((_, i) => (
                  <span
                    key={i}
                    className={`h-1.5 flex-1 rounded-full ${
                      i < Math.round(value) ? "bg-gold" : "bg-cream-deep"
                    }`}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
