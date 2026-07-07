// Small labeled pill. Color always ships with text — never color alone.
export function Chip({
  label,
  bg,
  fg,
  title,
}: {
  label: string;
  bg: string;
  fg: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-4"
      style={{ background: bg, color: fg }}
    >
      {label}
    </span>
  );
}
