"use client";

import { useState } from "react";
import type { DimensionScores, FacultyReview } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";

const DIMENSIONS = Object.keys(DIMENSION_LABELS) as Array<keyof DimensionScores>;
const DEFAULT_DIMENSIONS: DimensionScores = {
  evidence_integration: 2,
  assumption_testing: 2,
  counterargument_use: 2,
  reflection_depth: 2,
};

function Stepper({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-ink-soft">{label}</span>
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            aria-pressed={value === n}
            className="flex h-7 w-7 items-center justify-center rounded-full border text-xs font-medium transition"
            style={
              value === n
                ? { background: "var(--color-teal)", color: "var(--color-cream)", borderColor: "var(--color-teal)" }
                : { background: "var(--color-card)", color: "var(--color-ink-soft)", borderColor: "var(--color-line)" }
            }
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ReviewForm({
  sessionId,
  initialReview,
}: {
  sessionId: string;
  initialReview: FacultyReview | null;
}) {
  const [review, setReview] = useState<FacultyReview | null>(initialReview);
  const [editing, setEditing] = useState(!initialReview);
  const [reviewerName, setReviewerName] = useState(initialReview?.reviewerName ?? "");
  const [dimensions, setDimensions] = useState<DimensionScores>(
    initialReview?.dimensions ?? DEFAULT_DIMENSIONS
  );
  const [comments, setComments] = useState(initialReview?.comments ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch("/api/faculty/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessionId, reviewerName: reviewerName || "Faculty", dimensions, comments }),
      });
      if (!res.ok) throw new Error("Could not save the review");
      const saved: FacultyReview = await res.json();
      setReview(saved);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  if (!editing && review) {
    return (
      <div className="rounded-lg border border-line bg-cream-deep p-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-ink">
            Reviewed by {review.reviewerName}
          </p>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-xs font-medium text-teal hover:underline"
          >
            Edit review
          </button>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft">
          {DIMENSIONS.map((dim) => (
            <span key={dim}>
              {DIMENSION_LABELS[dim]}: <span className="font-mono text-ink">{review.dimensions[dim]}</span>
            </span>
          ))}
        </div>
        {review.comments ? <p className="mt-2 text-xs italic text-ink-soft">&ldquo;{review.comments}&rdquo;</p> : null}
        <p className="mt-2 text-[11px] text-slate-mid">
          {new Date(review.createdAt).toLocaleString()} · feeds convergent-validity measurement
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line p-4">
      <label className="block text-xs text-ink-soft">
        Reviewer name
        <input
          type="text"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          placeholder="Prof. Alvarez"
          className="mt-1 w-full rounded-md border border-line bg-card px-2.5 py-1.5 text-sm text-ink"
        />
      </label>

      <div className="mt-3 space-y-2.5">
        {DIMENSIONS.map((dim) => (
          <Stepper
            key={dim}
            label={DIMENSION_LABELS[dim]}
            value={dimensions[dim]}
            onChange={(v) => setDimensions((d) => ({ ...d, [dim]: v }))}
          />
        ))}
      </div>

      <label className="mt-3 block text-xs text-ink-soft">
        Comments
        <textarea
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={3}
          placeholder="Notes on this session's reasoning…"
          className="mt-1 w-full rounded-md border border-line bg-card px-2.5 py-1.5 text-sm text-ink"
        />
      </label>

      <p className="mt-2 text-[11px] text-slate-mid">
        This rubric assessment is paired against the platform&apos;s own score for this session to
        measure convergent validity.
      </p>

      {error ? <p className="mt-2 text-xs text-brick">{error}</p> : null}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={submit}
          disabled={saving}
          className="rounded-md bg-ink px-4 py-1.5 text-xs font-medium text-cream transition hover:bg-ink-soft disabled:opacity-60"
        >
          {saving ? "Saving…" : "Submit review"}
        </button>
        {review ? (
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-md border border-line px-4 py-1.5 text-xs font-medium text-ink hover:bg-cream-deep"
          >
            Cancel
          </button>
        ) : null}
      </div>
    </div>
  );
}
