"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { StudentDrilldown } from "@/lib/types";
import { SessionCard } from "./SessionCard";

export function StudentDrilldownView({ studentId }: { studentId: string }) {
  const [drilldown, setDrilldown] = useState<StudentDrilldown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/faculty/students/${studentId}`)
      .then((r) => {
        if (!r.ok) throw new Error("Student not found");
        return r.json();
      })
      .then((json) => {
        if (!cancelled) setDrilldown(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [studentId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-14">
        <p className="animate-pulse text-sm text-slate-mid">Loading student…</p>
      </div>
    );
  }

  if (error || !drilldown) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-14">
        <div className="cos-card border-l-4 p-4" style={{ borderLeftColor: "var(--color-brick)" }}>
          <p className="text-sm text-ink">{error ?? "Student not found"}</p>
          <Link href="/faculty" className="mt-2 inline-block text-xs font-medium text-teal hover:underline">
            ← Back to faculty dashboard
          </Link>
        </div>
      </div>
    );
  }

  const { student, sessions } = drilldown;
  const orderedSessions = [...sessions].sort((a, b) =>
    a.assignment.code.localeCompare(b.assignment.code, undefined, { numeric: true })
  );

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <Link href="/faculty" className="text-xs font-medium text-teal hover:underline">
        ← Back to faculty dashboard
      </Link>

      <div className="mt-3">
        <p className="cos-kicker">{student.cohort}</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink">{student.name}</h1>
        <p className="mt-1 text-sm text-ink-soft">{student.email}</p>
      </div>

      {orderedSessions.length === 0 ? (
        <p className="mt-8 text-sm text-slate-mid">No sessions recorded for this student yet.</p>
      ) : (
        <div className="mt-8 space-y-5">
          {orderedSessions.map((entry) => (
            <SessionCard key={entry.session.id} studentId={student.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
