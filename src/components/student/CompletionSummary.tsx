import {
  DIMENSION_LABELS,
  type IndependenceComponents,
  type Milestone,
  type SessionScores,
} from "@/lib/types";
import { MilestoneTimeline } from "./MilestoneTimeline";

const COMPONENT_LABELS: Record<keyof IndependenceComponents, string> = {
  origination: "Originated unprompted",
  unpromptedRigor: "Volunteered rigour",
  challengeResponse: "Under challenge",
  scaffoldIndependence: "Scaffold independence",
};

const COMPONENT_KEYS = Object.keys(COMPONENT_LABELS) as Array<keyof IndependenceComponents>;
const DIMENSION_KEYS = Object.keys(DIMENSION_LABELS) as Array<keyof typeof DIMENSION_LABELS>;

interface CompletionSummaryProps {
  scores: SessionScores;
  milestones: Milestone[];
}

export function CompletionSummary({ scores, milestones }: CompletionSummaryProps) {
  const index = Math.round(scores.independenceIndex);

  return (
    <div className="space-y-8">
      <div>
        <p className="cos-kicker">Session complete</p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">Your reasoning, in review</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          This is formative feedback on how you reasoned through the assignment — not a grade.
          It reflects how much of the thinking was yours, and how deeply you engaged with
          challenge, evidence, and reflection.
        </p>
      </div>

      <div className="cos-card p-6">
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-medium text-ink-soft">Independence Index</span>
          <span className="text-4xl font-semibold tabular-nums text-ink">{index}</span>
        </div>
        <div
          className="mt-3 h-2 w-full overflow-hidden rounded-full bg-cream-deep"
          role="progressbar"
          aria-valuenow={index}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Independence Index"
        >
          <div
            className="h-full rounded-full bg-teal"
            style={{ width: `${Math.min(100, Math.max(0, index))}%` }}
          />
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {COMPONENT_KEYS.map((key) => {
            const pct = Math.round(scores.independenceComponents[key] * 100);
            return (
              <div key={key}>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-ink-soft">{COMPONENT_LABELS[key]}</span>
                  <span className="text-xs tabular-nums text-slate-mid">{pct}%</span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-cream-deep">
                  <div
                    className="h-full rounded-full bg-gold"
                    style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="cos-kicker">Reasoning dimensions</p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          {DIMENSION_KEYS.map((key) => {
            const value = scores.dimensions[key];
            return (
              <div key={key} className="cos-card p-4">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-ink-soft">{DIMENSION_LABELS[key]}</span>
                  <span className="text-sm tabular-nums text-ink">{value.toFixed(1)} / 4</span>
                </div>
                <div className="mt-2 flex gap-1">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <span
                      key={i}
                      className={`h-1.5 flex-1 rounded-full ${
                        i < Math.round(value) ? "bg-gold" : "bg-cream-deep"
                      }`}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="cos-kicker">How your thinking developed</p>
        <div className="mt-3">
          <MilestoneTimeline milestones={milestones} />
        </div>
      </div>
    </div>
  );
}
