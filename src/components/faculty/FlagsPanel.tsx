"use client";

import { useState } from "react";
import Link from "next/link";
import type { CohortFlag, ScatterPoint } from "@/lib/types";

export function FlagsPanel({ flags, scatter }: { flags: CohortFlag[]; scatter: ScatterPoint[] }) {
  const nameFor = (id: string) => scatter.find((p) => p.studentId === id)?.studentName ?? id;

  if (flags.length === 0) {
    return (
      <div className="cos-card p-4 text-sm text-slate-mid">
        No cohort flags — nobody currently sits outside the depth / independence thresholds.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {flags.map((flag) => (
        <FlagCard key={flag.id} flag={flag} nameFor={nameFor} />
      ))}
    </div>
  );
}

function FlagCard({
  flag,
  nameFor,
}: {
  flag: CohortFlag;
  nameFor: (id: string) => string;
}) {
  const [open, setOpen] = useState(false);
  const isWarning = flag.severity === "warning";

  return (
    <div
      className="cos-card border-l-4 p-4"
      style={{ borderLeftColor: isWarning ? "var(--color-brick)" : "var(--color-teal)" }}
    >
      <p className="font-semibold text-ink">{flag.title}</p>
      <p className="mt-1 text-sm leading-relaxed text-ink-soft">{flag.description}</p>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mt-2 text-xs font-medium text-teal underline-offset-2 hover:underline"
        aria-expanded={open}
      >
        {open ? "Hide group" : "View group →"}
      </button>
      {open ? (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-2">
          {flag.studentIds.map((id) => (
            <li key={id}>
              <Link href={`/faculty/students/${id}`} className="text-sm text-ink underline-offset-2 hover:underline">
                {nameFor(id)}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
