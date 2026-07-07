export function InsightCallout({ insight }: { insight: string | null }) {
  return (
    <div
      className="cos-card border-l-4 p-4"
      style={{ borderLeftColor: "var(--color-gold)" }}
    >
      <p className="cos-kicker">Insight</p>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
        {insight ?? "Not enough scored sessions yet to surface a cohort insight."}
      </p>
    </div>
  );
}
