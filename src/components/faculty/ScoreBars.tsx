// Reusable 0-4 mini bar list — used for the four reasoning dimensions and for
// each of the three framework breakdown panels. One hue (teal), a lighter
// step of the same ramp for the unfilled track: a meter, not a categorical set.
export function ScoreBars({
  items,
  max = 4,
  dense = false,
}: {
  items: Array<{ key: string; label: string; value: number }>;
  max?: number;
  dense?: boolean;
}) {
  return (
    <ul className={dense ? "space-y-1.5" : "space-y-2.5"}>
      {items.map((item) => (
        <li key={item.key} className="flex items-center gap-3">
          <span className="w-40 shrink-0 truncate text-xs text-ink-soft">{item.label}</span>
          <span
            className="h-2 flex-1 overflow-hidden rounded-full"
            style={{ background: "var(--color-teal-soft)" }}
            role="img"
            aria-label={`${item.label}: ${item.value.toFixed(1)} of ${max}`}
          >
            <span
              className="block h-full rounded-full"
              style={{
                width: `${Math.min(100, Math.max(0, (item.value / max) * 100))}%`,
                background: "var(--color-teal)",
              }}
            />
          </span>
          <span className="w-8 shrink-0 text-right font-mono text-xs tabular-nums text-ink">
            {item.value.toFixed(1)}
          </span>
        </li>
      ))}
    </ul>
  );
}
