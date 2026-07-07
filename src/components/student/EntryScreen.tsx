"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Assignment, Course, Session, Student } from "@/lib/types";
import { EngineBadge } from "./EngineBadge";
import { formatDate } from "./constants";

interface Bootstrap {
  courses: Course[];
  assignments: Assignment[];
  students: Student[];
  engine: "claude" | "demo";
}

export function EntryScreen() {
  const router = useRouter();
  const [data, setData] = useState<Bootstrap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [studentId, setStudentId] = useState<string | null>(null);
  const [assignmentId, setAssignmentId] = useState<string | null>(null);

  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/bootstrap")
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load courses and students");
        return (await res.json()) as Bootstrap;
      })
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredStudents = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return data.students;
    return data.students.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.email.toLowerCase().includes(q) ||
        s.cohort.toLowerCase().includes(q)
    );
  }, [data, search]);

  const courseById = useMemo(() => {
    const map = new Map<string, Course>();
    data?.courses.forEach((c) => map.set(c.id, c));
    return map;
  }, [data]);

  const canStart = Boolean(studentId && assignmentId && !starting);

  async function handleStart() {
    if (!studentId || !assignmentId) return;
    setStarting(true);
    setStartError(null);
    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ studentId, assignmentId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? "Failed to start session");
      }
      const state = (await res.json()) as { session: Session };
      router.push(`/student/session/${state.session.id}`);
    } catch (err) {
      setStartError(err instanceof Error ? err.message : String(err));
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-14">
        <p className="text-sm text-ink-soft">Loading students and assignments…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-14">
        <div className="cos-card p-6">
          <p className="text-sm font-medium text-brick">{error ?? "Something went wrong."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="cos-kicker">Student experience · demo login</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
            Who&apos;s thinking today?
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
            Pick yourself from the roster and choose the assignment you want to reason through
            with your Socratic thinking partner.
          </p>
        </div>
        <EngineBadge engine={data.engine} />
      </div>

      <section className="mt-10">
        <p className="cos-kicker">01 — Choose your name</p>
        <label htmlFor="student-search" className="sr-only">
          Search students
        </label>
        <input
          id="student-search"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, cohort, or email…"
          className="mt-3 w-full max-w-sm rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-slate-mid focus:border-gold focus:outline-none focus:ring-2 focus:ring-gold/30"
        />

        <div
          role="listbox"
          aria-label="Students"
          className="mt-4 grid max-h-72 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3"
        >
          {filteredStudents.length === 0 && (
            <p className="text-sm text-ink-soft">No students match &quot;{search}&quot;.</p>
          )}
          {filteredStudents.map((s) => {
            const selected = s.id === studentId;
            return (
              <button
                key={s.id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => setStudentId(s.id)}
                className={`rounded-lg border px-3 py-2.5 text-left text-sm transition ${
                  selected
                    ? "border-gold bg-gold-soft text-ink"
                    : "border-line bg-card text-ink-soft hover:bg-cream-deep"
                }`}
              >
                <span className="block font-medium text-ink">{s.name}</span>
                <span className="block text-xs text-slate-mid">{s.cohort}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="mt-10">
        <p className="cos-kicker">02 — Choose an assignment</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {data.assignments.map((a) => {
            const selected = a.id === assignmentId;
            const course = courseById.get(a.courseId);
            return (
              <button
                key={a.id}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => setAssignmentId(a.id)}
                className={`cos-card rounded-lg p-4 text-left transition ${
                  selected ? "border-gold ring-2 ring-gold/30" : "hover:bg-cream-deep"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="cos-kicker">
                    {a.code}
                    {course ? ` · ${course.code}` : ""}
                  </span>
                  <span className="shrink-0 text-xs text-slate-mid">
                    Due {formatDate(a.dueDate)}
                  </span>
                </div>
                <h3 className="mt-1.5 text-sm font-semibold text-ink">{a.title}</h3>
                <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-ink-soft">
                  {a.prompt}
                </p>
              </button>
            );
          })}
          {data.assignments.length === 0 && (
            <p className="text-sm text-ink-soft">No assignments are available yet.</p>
          )}
        </div>
      </section>

      <section className="mt-10 flex flex-col items-start gap-3">
        <button
          type="button"
          disabled={!canStart}
          onClick={handleStart}
          className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-cream transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {starting ? "Starting…" : "Start thinking session →"}
        </button>
        {startError && (
          <p className="text-xs font-medium text-brick" role="alert">
            {startError}
          </p>
        )}
      </section>
    </div>
  );
}
