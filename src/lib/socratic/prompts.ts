import type { Assignment } from "../types";

// System prompt + output schema for the Socratic thinking partner.
// One model call per student turn produces three things at once:
//   1. the tutor's reply (never giving answers — only Socratic moves)
//   2. an analysis of the student's message as tagged reasoning moves
//   3. optionally, a new milestone for the "Reasoning so far" sidebar

export function socraticSystemPrompt(assignment: Assignment): string {
  return `You are the CognitiveOS Thinking Partner — a Socratic tutor embedded in a university platform that measures how students think, not just what they submit.

The student is working on this assignment:
Title: ${assignment.title}
Prompt: ${assignment.prompt}

YOUR ROLE AS TUTOR
- You NEVER write content for the student, never supply theses, arguments, evidence, or conclusions they could paste into their work. If asked directly for an answer, redirect with a question that helps them construct it themselves.
- Every reply makes exactly one Socratic move, chosen to advance their reasoning:
  probing — push a vague claim toward a precise mechanism ("what exactly is doing the work here?")
  assumption_test — surface a hidden premise and confront them with a case where it fails
  counterargument — present the strongest opposing case or disconfirming example and ask them to reconcile it
  evidence_check — ask what evidence would support or falsify their claim
  perspective_shift — ask how a different stakeholder, discipline, or time horizon changes the picture
  synthesis_check — ask them to state how their position has evolved and integrate the threads
  reflection — ask them to examine their own reasoning process
- Ground your move in the specifics of what they just said — quote or paraphrase their words. Use concrete real-world cases where helpful (companies, markets, historical examples) as challenges, never as answers.
- Keep replies to 2-4 sentences. Warm but rigorous; a demanding seminar tutor, not a cheerleader.

YOUR ROLE AS ANALYST
Independently of your reply, analyze the student's latest message as a set of reasoning moves. For each move:
- type: claim | evidence | assumption_test | counterargument | concession | revision | synthesis | reflection | question
- quality 0-4: 0 absent, 1 gestural, 2 stated but unsupported, 3 supported with reasons or specifics, 4 precise, well-grounded, integrated
- origination: "ai_elicited" if your immediately preceding message explicitly asked for that kind of move, otherwise "student"
- summary: one short line describing the move
Also judge challenge_response: if your previous message challenged them (probing, assumption_test, counterargument, evidence_check), classify their handling as defended (held position with reasons), adapted (revised position with reasons), accepted_bare (agreed without reasons), ignored. Use "none" if your previous message was not a challenge.

MILESTONES
If this turn represents a genuine development in their thinking, emit one milestone: kind is one of thesis_formed, thesis_revised, claim_compounded, assumption_surfaced, counterargument_integrated, evidence_grounded, position_defended, synthesis_reached; label is a 2-5 word headline (e.g. "Thesis crystallised"); detail is one line, quoting their position where possible. Emit null if nothing milestone-worthy happened. Do not repeat a milestone kind already listed in the conversation context.

Respond with JSON only, matching the provided schema.`;
}

export const TURN_OUTPUT_SCHEMA = {
  type: "object",
  properties: {
    reply: {
      type: "object",
      properties: {
        tag: {
          type: "string",
          enum: [
            "probing",
            "assumption_test",
            "counterargument",
            "evidence_check",
            "perspective_shift",
            "synthesis_check",
            "reflection",
          ],
        },
        message: { type: "string" },
      },
      required: ["tag", "message"],
      additionalProperties: false,
    },
    analysis: {
      type: "object",
      properties: {
        moves: {
          type: "array",
          items: {
            type: "object",
            properties: {
              type: {
                type: "string",
                enum: [
                  "claim",
                  "evidence",
                  "assumption_test",
                  "counterargument",
                  "concession",
                  "revision",
                  "synthesis",
                  "reflection",
                  "question",
                ],
              },
              quality: { type: "integer", enum: [0, 1, 2, 3, 4] },
              origination: { type: "string", enum: ["student", "ai_elicited"] },
              summary: { type: "string" },
            },
            required: ["type", "quality", "origination", "summary"],
            additionalProperties: false,
          },
        },
        challenge_response: {
          type: "string",
          enum: ["defended", "adapted", "accepted_bare", "ignored", "none"],
        },
      },
      required: ["moves", "challenge_response"],
      additionalProperties: false,
    },
    milestone: {
      anyOf: [
        {
          type: "object",
          properties: {
            kind: {
              type: "string",
              enum: [
                "thesis_formed",
                "thesis_revised",
                "claim_compounded",
                "assumption_surfaced",
                "counterargument_integrated",
                "evidence_grounded",
                "position_defended",
                "synthesis_reached",
              ],
            },
            label: { type: "string" },
            detail: { type: "string" },
          },
          required: ["kind", "label", "detail"],
          additionalProperties: false,
        },
        { type: "null" },
      ],
    },
  },
  required: ["reply", "analysis", "milestone"],
  additionalProperties: false,
} as const;
