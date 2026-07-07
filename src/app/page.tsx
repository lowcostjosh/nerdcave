import Link from "next/link";

// Landing page: role entry points + the platform story in one screen.

const PILLARS = [
  {
    n: "01",
    kicker: "Student experience",
    title: "Socratic AI",
    body: "A thinking partner that never writes the answer. It probes claims, stress-tests assumptions, and raises counterarguments — every reply is a deliberate Socratic move.",
  },
  {
    n: "02",
    kicker: "Data capture",
    title: "Reasoning Trace",
    body: "Every session is captured as a sequence of tagged reasoning moves — claims, evidence, assumption tests, counterarguments, revisions — not just chat logs.",
  },
  {
    n: "03",
    kicker: "Analysis layer",
    title: "Multi-Framework Scoring",
    body: "Traces are scored against the AAC&U Critical Thinking VALUE rubric, Paul-Elder intellectual standards, and Bloom's taxonomy — three systems, one validated score.",
  },
  {
    n: "04",
    kicker: "Novel output",
    title: "Independence Index",
    body: "A 0–100 measure of reasoning ownership: how much of the intellectual work originated with the student versus being scaffolded out of them by the AI.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-14">
      <section className="max-w-3xl">
        <p className="cos-kicker">The problem to be solved</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">
          Faculty can no longer verify{" "}
          <em className="font-serif italic text-ink-soft">whether work was actually thought.</em>
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-soft">
          AI produces graduate-level essays in minutes. Assessments can detect whether output looks
          correct — not whether the reasoning belongs to the student. CognitiveOS is the first
          platform that tells you whether a student actually thinks: it makes the reasoning process
          itself the assessed artifact.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/student"
            className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-cream transition hover:bg-ink-soft"
          >
            Enter as student →
          </Link>
          <Link
            href="/faculty"
            className="rounded-lg border border-line bg-card px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-cream-deep"
          >
            Enter as faculty →
          </Link>
        </div>
      </section>

      <section className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PILLARS.map((p) => (
          <div key={p.n} className="cos-card p-5">
            <div className="flex items-baseline justify-between">
              <p className="cos-kicker">{p.kicker}</p>
              <span className="font-mono text-xs text-slate-mid">{p.n}</span>
            </div>
            <h2 className="mt-2 text-lg font-semibold text-ink">{p.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">{p.body}</p>
          </div>
        ))}
      </section>

      <section className="mt-16 rounded-xl bg-ink px-6 py-5 text-cream">
        <p className="text-sm italic leading-relaxed text-cream/90">
          “The value of a credential depends on assessors knowing what they are assessing. While
          others try to catch cheaters, we make the reasoning visible — so there is nothing to
          catch.”
        </p>
        <p className="mt-2 text-xs text-cream/60">
          CognitiveOS · Cambridge pilot · validation design: every session generates an Independence
          Index and a faculty rubric assessment, measured for convergent validity.
        </p>
      </section>
    </div>
  );
}
