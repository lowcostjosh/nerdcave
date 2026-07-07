// A single headline stat — label, value, optional caption. No sparkline/delta
// needed here (the cohort dashboard's stat row is a snapshot, not a trend).
export function StatTile({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption?: string;
}) {
  return (
    <div className="cos-card p-5">
      <p className="cos-kicker">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
      {caption ? <p className="mt-1 text-xs text-slate-mid">{caption}</p> : null}
    </div>
  );
}
