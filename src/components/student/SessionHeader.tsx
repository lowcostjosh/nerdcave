"use client";

import { useState } from "react";
import type { Assignment, Session, Student } from "@/lib/types";
import { formatDate } from "./constants";

interface SessionHeaderProps {
  assignment: Assignment;
  student: Student;
  session: Session;
}

export function SessionHeader({ assignment, student, session }: SessionHeaderProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="cos-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="cos-kicker">{assignment.code} · due {formatDate(assignment.dueDate)}</p>
          <h1 className="mt-1 text-xl font-semibold text-ink">{assignment.title}</h1>
          <p className="mt-1 text-sm text-ink-soft">{student.name}</p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
            session.status === "completed"
              ? "bg-teal-soft text-teal"
              : "bg-gold-soft text-gold"
          }`}
        >
          {session.status === "completed" ? "Completed" : "In progress"}
        </span>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mt-3 flex items-center gap-1.5 text-xs font-medium text-ink-soft transition hover:text-ink"
      >
        <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>
          ›
        </span>
        {open ? "Hide assignment prompt" : "Show assignment prompt"}
      </button>

      {open && (
        <p className="mt-3 whitespace-pre-wrap rounded-lg border border-line bg-cream-deep p-4 text-sm leading-relaxed text-ink-soft">
          {assignment.prompt}
        </p>
      )}
    </div>
  );
}
