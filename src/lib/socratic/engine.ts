import Anthropic from "@anthropic-ai/sdk";
import type {
  Assignment,
  ChatMessage,
  MilestoneKind,
  QuickAction,
  SocraticTag,
  TurnAnalysis,
} from "../types";
import { socraticSystemPrompt, TURN_OUTPUT_SCHEMA } from "./prompts";
import {
  heuristicAnalyze,
  heuristicMilestone,
  heuristicOpening,
  heuristicReply,
} from "./heuristics";

// The Socratic engine. One call per student turn returns the tutor reply, the
// reasoning-move analysis of the student's message, and (optionally) a new
// milestone. Uses the Claude API when ANTHROPIC_API_KEY is configured and a
// deterministic heuristic engine otherwise, so the platform runs end-to-end
// with zero credentials.

export interface TurnResult {
  reply: { tag: SocraticTag; message: string };
  analysis: Omit<TurnAnalysis, "messageId" | "sessionId">;
  milestone: { kind: MilestoneKind; label: string; detail: string } | null;
  engine: "claude" | "demo";
}

export function hasClaude(): boolean {
  return Boolean(process.env.ANTHROPIC_API_KEY);
}

export function openingMessage(assignment: Assignment): { tag: SocraticTag; message: string } {
  // The opening is templated in both modes — there is nothing to analyze yet.
  return heuristicOpening(assignment);
}

export async function runTurn(params: {
  assignment: Assignment;
  /** Full history BEFORE the new student message */
  history: ChatMessage[];
  studentText: string;
  quickAction: QuickAction | null;
  existingMilestoneKinds: Set<MilestoneKind>;
}): Promise<TurnResult> {
  const { assignment, history, studentText, quickAction, existingMilestoneKinds } = params;

  if (hasClaude()) {
    try {
      return await claudeTurn(params);
    } catch (err) {
      console.error("Claude turn failed, falling back to demo engine:", err);
    }
  }

  const analysis = heuristicAnalyze(studentText, lastAiTag(history), quickAction);
  return {
    reply: heuristicReply(assignment, history, analysis, quickAction, studentText),
    analysis,
    milestone: heuristicMilestone(analysis, studentText, existingMilestoneKinds),
    engine: "demo",
  };
}

function lastAiTag(history: ChatMessage[]): SocraticTag | null {
  for (let i = history.length - 1; i >= 0; i--) {
    if (history[i].role === "ai") return history[i].tag;
  }
  return null;
}

// ---------- Claude path ----------

let client: Anthropic | null = null;
function getClient(): Anthropic {
  if (!client) client = new Anthropic();
  return client;
}

const QUICK_ACTION_NOTE: Record<QuickAction, string> = {
  unpack_question: "The student pressed the 'Unpack question' scaffold — help them decompose the assignment prompt.",
  test_assumption: "The student pressed the 'Test assumption' scaffold — surface and stress a premise of their current position.",
  find_counterargument: "The student pressed the 'Find counterargument' scaffold — present the strongest opposing case.",
  compare_perspectives: "The student pressed the 'Compare perspectives' scaffold — shift the vantage point.",
  reflect: "The student pressed the 'Reflect' scaffold — turn their attention to their own reasoning process.",
};

async function claudeTurn(params: {
  assignment: Assignment;
  history: ChatMessage[];
  studentText: string;
  quickAction: QuickAction | null;
  existingMilestoneKinds: Set<MilestoneKind>;
}): Promise<TurnResult> {
  const { assignment, history, studentText, quickAction, existingMilestoneKinds } = params;

  const transcript = history
    .map((m) => (m.role === "ai" ? `TUTOR [${m.tag ?? "reply"}]: ${m.content}` : `STUDENT: ${m.content}`))
    .join("\n\n");

  const contextBits: string[] = [];
  if (existingMilestoneKinds.size > 0) {
    contextBits.push(`Milestone kinds already recorded (do not repeat): ${[...existingMilestoneKinds].join(", ")}`);
  }
  if (quickAction) contextBits.push(QUICK_ACTION_NOTE[quickAction]);

  const userContent = [
    transcript ? `Conversation so far:\n\n${transcript}` : "This is the first student message of the session.",
    contextBits.join("\n"),
    `STUDENT (latest message): ${studentText}`,
  ]
    .filter(Boolean)
    .join("\n\n");

  const response = await getClient().messages.create({
    model: "claude-opus-4-8",
    max_tokens: 4096,
    thinking: { type: "adaptive" },
    system: [
      {
        type: "text",
        text: socraticSystemPrompt(assignment),
        cache_control: { type: "ephemeral" },
      },
    ],
    messages: [{ role: "user", content: userContent }],
    output_config: {
      format: {
        type: "json_schema",
        schema: TURN_OUTPUT_SCHEMA as unknown as Record<string, unknown>,
      },
    },
  });

  if (response.stop_reason === "refusal") {
    throw new Error("Model refused the request");
  }

  const text = response.content.find((b) => b.type === "text");
  if (!text || text.type !== "text") throw new Error("No text block in response");

  const parsed = JSON.parse(text.text) as {
    reply: { tag: SocraticTag; message: string };
    analysis: {
      moves: TurnAnalysis["moves"];
      challenge_response: TurnAnalysis["challengeResponse"];
    };
    milestone: { kind: MilestoneKind; label: string; detail: string } | null;
  };

  return {
    reply: parsed.reply,
    analysis: {
      moves: parsed.analysis.moves,
      challengeResponse: parsed.analysis.challenge_response,
    },
    milestone:
      parsed.milestone && !existingMilestoneKinds.has(parsed.milestone.kind) ? parsed.milestone : null,
    engine: "claude",
  };
}
