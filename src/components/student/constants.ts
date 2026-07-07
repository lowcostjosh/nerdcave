import type { QuickAction, SocraticTag } from "@/lib/types";

// Presentation metadata for the Socratic move tags shown on AI messages.
// Colors are drawn from the CognitiveOS token set (gold / teal / brick / neutral).
export const TAG_META: Record<
  SocraticTag,
  { label: string; text: string; bg: string }
> = {
  orientation: { label: "ORIENTATION", text: "text-ink-soft", bg: "bg-cream-deep" },
  probing: { label: "PROBING", text: "text-ink-soft", bg: "bg-cream-deep" },
  assumption_test: { label: "ASSUMPTION TEST", text: "text-gold", bg: "bg-gold-soft" },
  counterargument: { label: "COUNTERARGUMENT", text: "text-brick", bg: "bg-brick-soft" },
  evidence_check: { label: "EVIDENCE CHECK", text: "text-teal", bg: "bg-teal-soft" },
  perspective_shift: { label: "PERSPECTIVE SHIFT", text: "text-gold", bg: "bg-gold-soft" },
  synthesis_check: { label: "SYNTHESIS CHECK", text: "text-teal", bg: "bg-teal-soft" },
  reflection: { label: "REFLECTION", text: "text-ink-soft", bg: "bg-cream-deep" },
};

export const QUICK_ACTION_META: Record<
  QuickAction,
  { label: string; hint: string }
> = {
  unpack_question: {
    label: "Unpack question",
    hint: "Break the prompt into its component questions before answering.",
  },
  test_assumption: {
    label: "Test assumption",
    hint: "Surface and stress-test an assumption behind your claim.",
  },
  find_counterargument: {
    label: "Find counterargument",
    hint: "Look for the strongest counterargument to your own position.",
  },
  compare_perspectives: {
    label: "Compare perspectives",
    hint: "Consider how someone with a different view would see this.",
  },
  reflect: {
    label: "Reflect",
    hint: "Step back and reflect on how your thinking has moved.",
  },
};

export function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
