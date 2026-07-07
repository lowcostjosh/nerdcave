"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";
import { TagChip } from "./TagChip";
import { formatTime } from "./constants";

interface ChatThreadProps {
  messages: ChatMessage[];
  pending: boolean;
}

export function ChatThread({ messages, pending }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  return (
    <div className="flex flex-col gap-4 overflow-y-auto px-1 py-2" aria-live="polite">
      {messages.length === 0 && !pending && (
        <p className="py-8 text-center text-sm text-ink-soft">
          Your thinking partner hasn&apos;t opened the conversation yet.
        </p>
      )}

      {messages.map((message) => {
        const isStudent = message.role === "student";
        return (
          <div
            key={message.id}
            className={`flex flex-col ${isStudent ? "items-end" : "items-start"}`}
          >
            {!isStudent && message.tag && (
              <div className="mb-1.5 ml-1">
                <TagChip tag={message.tag} />
              </div>
            )}
            <div
              className={`max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%] ${
                isStudent
                  ? "rounded-br-sm bg-ink text-cream"
                  : "cos-card rounded-bl-sm text-ink"
              }`}
            >
              {message.content}
            </div>
            <div className="mt-1 flex items-center gap-2 px-1 text-[0.7rem] text-slate-mid">
              {message.quickAction && (
                <span className="italic">via quick action</span>
              )}
              <span>{formatTime(message.createdAt)}</span>
            </div>
          </div>
        );
      })}

      {pending && (
        <div className="flex items-start">
          <div className="cos-card flex items-center gap-2 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-ink-soft">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-mid [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-mid [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-mid" />
            </span>
            Thinking partner is considering…
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
