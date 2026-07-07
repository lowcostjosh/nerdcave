"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Course, FacultyOverview, ValidityStats } from "@/lib/types";
import { StatTile } from "./StatTile";
import { Heatmap } from "./Heatmap";
import { InsightCallout } from "./InsightCallout";
import { CohortScatter } from "./CohortScatter";
import { FlagsPanel } from "./FlagsPanel";
import { ValidityPanel } from "./ValidityPanel";

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

export function FacultyDashboard({ initialCourseId }: { initialCourseId?: string }) {
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [courseId, setCourseId] = useState<string | undefined>(initialCourseId);
  const [overview, setOverview] = useState<FacultyOverview | null>(null);
  const [validity, setValidity] = useState<ValidityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    fetch("/api/bootstrap")
      .then((r) => r.json())
      .then((data) => setCourses(data.courses ?? []))
      .catch(() => {
        /* course switcher is a nicety — overview still loads without it */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const qs = courseId ? `?courseId=${encodeURIComponent(courseId)}` : "";
    Promise.all([
      fetch(`/api/faculty/overview${qs}`).then((r) => {
        if (!r.ok) throw new Error("Failed to load cohort overview");
        return r.json();
      }),
      fetch("/api/faculty/validity").then((r) => {
        if (!r.ok) throw new Error("Failed to load validity stats");
        return r.json();
      }),
    ])
      .then(([overviewData, validityData]) => {
        if (cancelled) return;
        setOverview(overviewData);
        setValidity(validityData);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, attempt]);

  if (loading && !overview) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-14">
        <p className="cos-kicker">Faculty dashboard</p>
        <p className="mt-3 animate-pulse text-sm text-slate-mid">Loading cohort data…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-14">
        <p className="cos-kicker">Faculty dashboard</p>
        <div className="cos-card mt-4 border-l-4 p-4" style={{ borderLeftColor: "var(--color-brick)" }}>
          <p className="text-sm text-ink">{error}</p>
          <button
            type="button"
            onClick={() => setAttempt((a) => a + 1)}
            className="mt-2 rounded-md border border-line px-3 py-1 text-xs font-medium text-ink hover:bg-cream-deep"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-14">
        <p className="cos-kicker">Faculty dashboard</p>
        <p className="mt-3 text-sm text-slate-mid">No course data available yet.</p>
      </div>
    );
  }

  const meanIndependence = Math.round(mean(overview.scatter.map((p) => p.independence)));
  const meanDepth = mean(overview.scatter.map((p) => p.depth));

  return (
    <div className="mx-auto max-w-7xl px-6 py-14">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="cos-kicker">{overview.course.code} · {overview.course.term}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Where the cohort is strengthening — and where they need teaching
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-ink-soft">{overview.course.title}</p>
        </div>
        {courses && courses.length > 1 ? (
          <label className="text-xs text-slate-mid">
            <span className="mr-2 uppercase tracking-wide">Course</span>
            <select
              value={overview.course.id}
              onChange={(e) => {
                setCourseId(e.target.value);
                router.replace(`/faculty?courseId=${e.target.value}`);
              }}
              className="rounded-md border border-line bg-card px-2 py-1.5 text-sm text-ink"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {c.title}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Students" value={String(overview.studentCount)} />
        <StatTile label="Sessions analysed" value={String(overview.sessionCount)} />
        <StatTile
          label="Cohort mean Independence Index"
          value={overview.scatter.length ? String(meanIndependence) : "—"}
          caption="0–100"
        />
        <StatTile
          label="Cohort mean depth"
          value={overview.scatter.length ? meanDepth.toFixed(1) : "—"}
          caption="0–4.0"
        />
      </div>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">Reasoning heatmap</h2>
        <div className="mt-3 cos-card p-5">
          <Heatmap assignments={overview.assignments} heatmap={overview.heatmap} trends={overview.trends} />
        </div>
        <div className="mt-4">
          <InsightCallout insight={overview.insight} />
        </div>
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="cos-card p-5">
          <h2 className="text-lg font-semibold text-ink">Independence vs depth — cohort scatter</h2>
          <p className="mt-1 text-xs text-slate-mid">
            One dot per student, averaged across their sessions in this course.
          </p>
          <div className="mt-4">
            <CohortScatter scatter={overview.scatter} flags={overview.flags} />
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-ink">Cohort flags</h2>
          <div className="mt-3">
            <FlagsPanel flags={overview.flags} scatter={overview.scatter} />
          </div>
        </div>
      </section>

      {validity ? (
        <section className="mt-10">
          <ValidityPanel stats={validity} />
        </section>
      ) : null}
    </div>
  );
}
