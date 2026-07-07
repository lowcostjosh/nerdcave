# CognitiveOS

**Reasoning infrastructure for higher education** — a platform that measures *how students think*, not just what they submit.

AI can produce a graduate-level essay in minutes, so assessment can no longer infer thinking from output. CognitiveOS inverts the problem: instead of trying to catch AI-written work, it makes the reasoning process itself the assessed artifact. Students work through assignments with a Socratic AI that never gives answers; every session produces an auditable reasoning trace, multi-framework scores, and an **Independence Index** — a measure of how much of the intellectual work actually belonged to the student.

Built as the working platform for the CognitiveOS venture (Cambridge Judge Business School, MBA35C Entrepreneurship).

## Quick start

```bash
npm install
npm run dev
```

Open http://localhost:3000. That's it — with no configuration the platform runs on a built-in deterministic demo engine and self-seeds a realistic 40-student pilot cohort (course MBA35C, three assignments) on first boot, so both the student workspace and the faculty dashboard are fully populated.

To run the Socratic tutor and turn analysis on the live Claude API instead:

```bash
cp .env.example .env.local   # add your ANTHROPIC_API_KEY
```

The engine badge in the UI shows which mode is active. If a live API call fails mid-session, the turn falls back to the demo engine rather than erroring.

To reset all data, delete `data/cognitiveos.db*` and restart.

## The four layers

| # | Layer | What it does |
|---|-------|--------------|
| 01 | **Socratic AI** (student experience) | A thinking partner that makes exactly one Socratic move per reply — probing, assumption testing, counterargument, evidence check, perspective shift, synthesis check, reflection — and never supplies content the student could paste into their work. Quick-action chips (Unpack question, Test assumption, …) are available as scaffolds, and their use is recorded. |
| 02 | **Reasoning Trace** (data capture) | Every student message is analyzed into tagged reasoning moves — claim, evidence, assumption test, counterargument, concession, revision, synthesis, reflection — each with a 0–4 quality and an origination marker (student-originated vs AI-elicited). Milestones ("Thesis crystallised", "Counterargument integrated", …) appear live in the student's *Reasoning so far* sidebar. |
| 03 | **Multi-Framework Scoring** (analysis) | Traces are scored deterministically against three academic frameworks — the AAC&U Critical Thinking VALUE rubric, Paul-Elder intellectual standards, and Bloom's taxonomy — and rolled up into four cohort dimensions: evidence integration, assumption testing, counterargument use, reflection depth. |
| 04 | **Independence Index** (novel output) | A 0–100 measure of reasoning ownership computed from the trace: origination share (35%), unprompted rigour (30%), response under challenge (25%), scaffold independence (10%). Deterministic and auditable — every point traces back to specific moves in the transcript. |

## The two surfaces

**Student workspace** (`/student`) — pick your name and an assignment, then work through it in the Socratic chat. The right sidebar shows your reasoning milestones and live signals (Independence Index + dimension scores) updating every turn. Completing a session produces a formative summary, not a grade.

**Faculty dashboard** (`/faculty`) — "where the cohort is strengthening and where they need teaching": a dimension × assignment heatmap with trend directions, an automatic teaching insight, an independence-vs-depth scatter with flagged groups (dependency pattern: strong output that needed heavy scaffolding; below-both-thresholds; exemplars), and per-student drilldowns with the full audited reasoning trace. Faculty can score any session on the same four-dimension rubric; the platform reports the convergent validity (Pearson r) between its scores and faculty judgment — the pilot's validation design.

## Architecture

```
src/lib/
  types.ts               domain contract shared by engine, API, and both UIs
  db.ts                  SQLite (better-sqlite3), schema init + first-boot seeding
  repo.ts                data access layer
  seed.ts                deterministic 40-student demo cohort generator
  socratic/
    prompts.ts           system prompt + structured-output schema for the tutor
    engine.ts            one Claude call per turn -> reply + move analysis + milestone
    heuristics.ts        deterministic fallback engine (demo mode, zero credentials)
  scoring/
    frameworks.ts        moves -> dimensions + AAC&U / Paul-Elder / Bloom scores
    independence.ts      moves + transcript -> Independence Index (0-100)
  sessions.ts            turn orchestration (store, analyze, reply, rescore)
  faculty.ts             cohort analytics: heatmap, trends, scatter, flags, validity
src/app/api/             thin route handlers over src/lib
src/app/student/         student workspace UI
src/app/faculty/         faculty dashboard UI
```

Stack: Next.js (App Router) · TypeScript · Tailwind CSS 4 · better-sqlite3 · Anthropic TypeScript SDK (`claude-opus-4-8` with adaptive thinking and structured outputs).

Design decisions worth knowing:

- **One model call per turn.** The tutor reply, the reasoning-move analysis of the student's message, and any milestone come back in a single structured-output response, so the trace can never drift out of sync with the conversation.
- **Scoring is deterministic over the trace.** The LLM (or heuristic) tags moves; everything downstream — dimensions, framework scores, Independence Index — is pure functions of those tags. Same trace, same score, fully auditable.
- **Demo mode is a first-class citizen.** The heuristic engine implements the same interface as the Claude path, which is also what makes the seeded cohort internally consistent: seeded transcripts are analyzed by the same code that analyzes live ones.

## API

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/bootstrap` | Courses, assignments, roster, engine mode |
| POST | `/api/sessions` | Find/create a session (returns opening message) |
| GET | `/api/sessions/:id` | Full session state |
| POST | `/api/sessions/:id/messages` | Post a student turn → AI reply, milestone, live scores |
| POST | `/api/sessions/:id/complete` | Finalize a session |
| GET | `/api/faculty/overview` | Heatmap, trends, scatter, flags, insight |
| GET | `/api/faculty/students/:id` | Drilldown (`?sessionId=` for the full trace) |
| POST | `/api/faculty/reviews` | Faculty rubric review of a session |
| GET | `/api/faculty/validity` | Platform-vs-faculty convergent validity |
