"use client";

import { useEffect, useState } from "react";
import type { ChatMessage, ReasoningMove, TurnAnalysis } from "@/lib/types";
import { QualityDots } from "./QualityDots";
import { Chip } from "./Chip";
import { humanizeKey } from "./colors";

interface TraceData {
  messages: ChatMessage[];
  analyses: TurnAnalysis[];
}

const CHALLENGE_LABELS: Record<string, string> = {
  defended: "Defended the challenge with reasons",
  adapted: "Adapted position with reasons",
  accepted_bare: "Accepted the challenge without reasons",
  ignored: "Ignored the challenge",
};

function MoveRow({ move }: { move: ReasoningMove }) {
  const isStudentOriginated = move.origination === "student";
  return (
    <li className="flex flex-wrap items-start gap-2 rounded-md bg-cream-deep px-2.5 py-2">
      <Chip label={humanizeKey(move.type)} bg="var(--color-gold-soft)" fg="var(--color-ink)" />
      <QualityDots quality={move.quality} />
      <Chip
        label={isStudentOriginated ? "Student-originated" : "AI-elicited"}
        bg={isStudentOriginated ? "var(--color-teal-soft)" : "var(--color-cream-deep)"}
        fg={isStudentOriginated ? "var(--color-teal)" : "var(--color-slate-mid)"}
      />
      <p className="w-full text-xs leading-relaxed text-ink-soft">{move.summary}</p>
    </li>
  );
}

export function TraceViewer({ studentId, sessionId }: { studentId: string; sessionId: string }) {
  const [data, setData] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/faculty/students/${studentId}?sessionId=${sessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error("Could not load the reasoning trace");
        return r.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
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
  }, [studentId, sessionId]);

  if (loading) return <p className="animate-pulse text-xs text-slate-mid">Loading trace…</p>;
  if (error) return <p className="text-xs text-brick">{error}</p>;
  if (!data || data.messages.length === 0) {
    return <p className="text-xs text-slate-mid">No messages recorded for this session.</p>;
  }

  const analysisFor = (messageId: string) => data.analyses.find((a) => a.messageId === messageId);

  return (
    <ol className="space-y-3">
      {data.messages.map((m) => {
        const isAi = m.role === "ai";
        const analysis = !isAi ? analysisFor(m.id) : undefined;
        return (
          <li key={m.id} className={isAi ? "" : "border-l-2 pl-3"} style={!isAi ? { borderLeftColor: "var(--color-teal)" } : undefined}>
            <div
              className={`max-w-2xl rounded-lg px-3 py-2 text-sm leading-relaxed ${isAi ? "bg-cream-deep text-ink" : "bg-card text-ink"}`}
              style={!isAi ? { border: "1px solid var(--color-line)" } : undefined}
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-mid">
                  {isAi ? "Socratic AI" : "Student"}
                </span>
                {isAi && m.tag ? (
                  <Chip label={humanizeKey(m.tag)} bg="var(--color-gold-soft)" fg="var(--color-ink)" />
                ) : null}
                {!isAi && m.quickAction ? (
                  <Chip label={humanizeKey(m.quickAction)} bg="var(--color-cream-deep)" fg="var(--color-slate-mid)" />
                ) : null}
              </div>
              <p>{m.content}</p>
            </div>
            {analysis && analysis.moves.length > 0 ? (
              <div className="mt-1.5 max-w-2xl">
                <ul className="space-y-1.5">
                  {analysis.moves.map((move, i) => (
                    <MoveRow key={i} move={move} />
                  ))}
                </ul>
                {analysis.challengeResponse !== "none" ? (
                  <p className="mt-1 text-[11px] italic text-slate-mid">
                    {CHALLENGE_LABELS[analysis.challengeResponse]}
                  </p>
                ) : null}
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
