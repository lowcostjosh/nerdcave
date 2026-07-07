import type { FrameworkScores } from "@/lib/types";
import { ScoreBars } from "./ScoreBars";
import { humanizeKey } from "./colors";

function toItems(obj: object) {
  return Object.entries(obj as Record<string, number>).map(([key, value]) => ({
    key,
    label: humanizeKey(key),
    value,
  }));
}

export function FrameworkBreakdown({ frameworks }: { frameworks: FrameworkScores }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="cos-card p-4">
        <p className="cos-kicker">AAC&amp;U VALUE rubric</p>
        <div className="mt-3">
          <ScoreBars items={toItems(frameworks.aacu)} dense />
        </div>
      </div>
      <div className="cos-card p-4">
        <p className="cos-kicker">Paul-Elder standards</p>
        <div className="mt-3">
          <ScoreBars items={toItems(frameworks.paulElder)} dense />
        </div>
      </div>
      <div className="cos-card p-4">
        <p className="cos-kicker">Bloom&apos;s taxonomy</p>
        <div className="mt-3">
          <ScoreBars items={toItems(frameworks.bloom)} dense />
        </div>
      </div>
    </div>
  );
}
