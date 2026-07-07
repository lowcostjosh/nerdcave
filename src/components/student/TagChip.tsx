import type { SocraticTag } from "@/lib/types";
import { TAG_META } from "./constants";

export function TagChip({ tag }: { tag: SocraticTag }) {
  const meta = TAG_META[tag];
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide ${meta.bg} ${meta.text}`}
    >
      {meta.label}
    </span>
  );
}
