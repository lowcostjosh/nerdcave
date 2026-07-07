export function EngineBadge({ engine }: { engine: "claude" | "demo" }) {
  const isLive = engine === "claude";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
        isLive
          ? "border-teal/30 bg-teal-soft text-teal"
          : "border-line bg-cream-deep text-ink-soft"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-teal" : "bg-slate-mid"}`}
        aria-hidden
      />
      {isLive ? "Live AI (Claude)" : "Demo engine"}
    </span>
  );
}
