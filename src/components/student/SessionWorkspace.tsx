"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { ChatMessage, Milestone, QuickAction, SessionScores, SessionState } from "@/lib/types";
import { ChatThread } from "./ChatThread";
import { Composer } from "./Composer";
import { CompletionSummary } from "./CompletionSummary";
import { ConfirmDialog } from "./ConfirmDialog";
import { LiveSignals } from "./LiveSignals";
import { MilestoneTimeline } from "./MilestoneTimeline";
import { SessionHeader } from "./SessionHeader";

interface PostMessageResult {
  studentMessage: ChatMessage;
  aiMessage: ChatMessage;
  newMilestone: Milestone | null;
  scores: SessionScores;
  engine: "claude" | "demo";
}

async function readError(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  return (body?.error as string | undefined) ?? fallback;
}

export function SessionWorkspace({ sessionId }: { sessionId: string }) {
  const [state, setState] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [pending, setPending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [completeError, setCompleteError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    fetch(`/api/sessions/${sessionId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(await readError(res, "Session not found"));
        return (await res.json()) as SessionState;
      })
      .then((data) => {
        if (!cancelled) setState(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const handleSend = useCallback(
    async (content: string, quickAction: QuickAction | null) => {
      setSendError(null);
      setPending(true);
      try {
        const res = await fetch(`/api/sessions/${sessionId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, quickAction }),
        });
        if (!res.ok) throw new Error(await readError(res, "Failed to send message"));
        const data = (await res.json()) as PostMessageResult;
        setState((prev) =>
          prev
            ? {
                ...prev,
                messages: [...prev.messages, data.studentMessage, data.aiMessage],
                milestones: data.newMilestone
                  ? [...prev.milestones, data.newMilestone]
                  : prev.milestones,
                scores: data.scores,
              }
            : prev
        );
      } catch (err) {
        setSendError(err instanceof Error ? err.message : String(err));
      } finally {
        setPending(false);
      }
    },
    [sessionId]
  );

  const handleComplete = useCallback(async () => {
    setCompleting(true);
    setCompleteError(null);
    try {
      const res = await fetch(`/api/sessions/${sessionId}/complete`, { method: "POST" });
      if (!res.ok) throw new Error(await readError(res, "Failed to complete session"));
      const data = (await res.json()) as SessionState;
      setState(data);
      setConfirmOpen(false);
    } catch (err) {
      setCompleteError(err instanceof Error ? err.message : String(err));
    } finally {
      setCompleting(false);
    }
  }, [sessionId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-14">
        <p className="text-sm text-ink-soft">Loading your session…</p>
      </div>
    );
  }

  if (loadError || !state) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="cos-card p-6">
          <p className="text-sm font-medium text-brick">{loadError ?? "Session not found"}</p>
          <Link
            href="/student"
            className="mt-4 inline-block rounded-lg border border-line bg-card px-4 py-2 text-sm font-medium text-ink transition hover:bg-cream-deep"
          >
            ← Back to start
          </Link>
        </div>
      </div>
    );
  }

  const { session, student, assignment, messages, milestones, scores } = state;
  const completed = session.status === "completed";
  const newestFirstMilestones = [...milestones].reverse();

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[1fr_320px]">
      <div className="flex min-h-0 flex-col gap-4">
        <SessionHeader assignment={assignment} student={student} session={session} />

        <div className="cos-card flex min-h-0 flex-1 flex-col p-4">
          <div className="h-[55vh] min-h-[280px] flex-1 overflow-y-auto sm:h-[60vh]">
            <ChatThread messages={messages} pending={pending} />
          </div>

          {sendError && (
            <p className="mt-2 text-xs font-medium text-brick" role="alert">
              {sendError}
            </p>
          )}

          {completed ? (
            <div className="mt-4 border-t border-line pt-4">
              <p className="text-sm text-ink-soft">
                This session is complete. Your formative feedback is in the summary below.
              </p>
            </div>
          ) : (
            <>
              <div className="mt-3 flex justify-end">
                <button
                  type="button"
                  onClick={() => setConfirmOpen(true)}
                  className="rounded-lg border border-line bg-card px-3 py-1.5 text-xs font-medium text-ink-soft transition hover:bg-cream-deep hover:text-ink"
                >
                  Complete session
                </button>
              </div>
              <Composer pending={pending} disabled={completed} onSend={handleSend} />
            </>
          )}
        </div>

        {completed && scores && (
          <div className="cos-card p-6">
            <CompletionSummary scores={scores} milestones={newestFirstMilestones} />
          </div>
        )}
        {completeError && (
          <p className="text-xs font-medium text-brick" role="alert">
            {completeError}
          </p>
        )}
      </div>

      <aside className="h-fit lg:sticky lg:top-20">
        <div className="cos-card p-5">
          <p className="cos-kicker">Reasoning so far</p>
          <h2 className="mt-1 text-sm font-semibold text-ink">
            How your thinking has developed
          </h2>
          <div className="mt-4 max-h-80 overflow-y-auto pr-1">
            <MilestoneTimeline milestones={newestFirstMilestones} />
          </div>

          <div className="mt-6 border-t border-line pt-5">
            <p className="cos-kicker">Live signals</p>
            <div className="mt-3">
              <LiveSignals scores={scores} />
            </div>
          </div>
        </div>
      </aside>

      <ConfirmDialog
        open={confirmOpen}
        title="Complete this session?"
        body="You won't be able to add further reasoning to this session afterwards. You'll see a formative summary of how your thinking developed."
        confirmLabel={completing ? "Completing…" : "Complete session"}
        onConfirm={handleComplete}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
