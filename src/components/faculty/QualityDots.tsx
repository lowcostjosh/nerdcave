// Five dots (0-4 quality) used inline on a reasoning move in the trace viewer.
export function QualityDots({ quality, max = 4 }: { quality: number; max?: number }) {
  return (
    <span
      className="inline-flex items-center gap-0.5 align-middle"
      role="img"
      aria-label={`Quality ${quality} of ${max}`}
    >
      {Array.from({ length: max + 1 }).map((_, i) => (
        <span
          key={i}
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{
            background: i <= quality ? "var(--color-teal)" : "var(--color-line)",
          }}
        />
      ))}
    </span>
  );
}
