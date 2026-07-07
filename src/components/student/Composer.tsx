"use client";

import { useState } from "react";
import type { QuickAction } from "@/lib/types";
import { QUICK_ACTION_META } from "./constants";

interface ComposerProps {
  pending: boolean;
  disabled?: boolean;
  onSend: (content: string, quickAction: QuickAction | null) => void;
}

const QUICK_ACTIONS = Object.keys(QUICK_ACTION_META) as QuickAction[];

export function Composer({ pending, disabled, onSend }: ComposerProps) {
  const [text, setText] = useState("");

  const canSend = text.trim().length > 0 && !pending && !disabled;

  const submit = (quickAction: QuickAction | null) => {
    const content = text.trim();
    if (!content || pending || disabled) return;
    onSend(content, quickAction);
    setText("");
  };

  return (
    <div className="border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-2">
        {QUICK_ACTIONS.map((action) => {
          const meta = QUICK_ACTION_META[action];
          return (
            <button
              key={action}
              type="button"
              title={meta.hint}
              disabled={!canSend}
              onClick={() => submit(action)}
              className="rounded-full border border-line bg-cream-deep px-3 py-1 text-xs font-medium text-ink-soft transition hover:bg-gold-soft hover:text-gold disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-cream-deep disabled:hover:text-ink-soft"
            >
              {meta.label}
            </button>
          );
        })}
      </div>
      <p className="mt-1.5 text-[0.7rem] text-slate-mid">
        Chips are scaffolds — write your own thinking first when you can. How much you lean on
        them factors into your Independence Index.
      </p>

      <div className="mt-3 flex items-end gap-2">
        <label htmlFor="composer-input" className="sr-only">
          Share what you&apos;re thinking about
        </label>
        <textarea
          id="composer-input"
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              submit(null);
            }
          }}
          placeholder="Share what you're thinking about…"
          rows={3}
          className="flex-1 resize-none rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-slate-mid focus:border-gold focus:outline-none focus:ring-2 focus:ring-gold/30 disabled:cursor-not-allowed disabled:bg-cream-deep disabled:text-slate-mid"
        />
        <button
          type="button"
          onClick={() => submit(null)}
          disabled={!canSend}
          className="h-fit rounded-lg bg-ink px-4 py-2.5 text-sm font-medium text-cream transition hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {pending ? "Sending…" : "Send"}
        </button>
      </div>
      <p className="mt-1 text-[0.7rem] text-slate-mid">
        Press {"⌘"}/Ctrl + Enter to send.
      </p>
    </div>
  );
}
