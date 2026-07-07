// Static cohort roster: course, assignments, students, and the persona +
// participation assignment that drives the transcript generator in seed.ts.
//
// Everything here is a fixed literal table — no randomness — so the roster
// itself is stable across runs. The generator (seed.ts) layers deterministic
// PRNG-driven content on top of this fixed skeleton.

export const COURSE = {
  code: "MBA35C",
  title: "Entrepreneurship",
  term: "Easter 2026",
};

export interface AssignmentDef {
  code: string;
  title: string;
  prompt: string;
  dueDate: string;
}

export const ASSIGNMENTS: AssignmentDef[] = [
  {
    code: "A1",
    title: "Platform competition",
    prompt:
      "Is a first-mover advantage in digital platform markets sustainable? Take a position and defend it with reference to at least two real platform businesses.",
    dueDate: "2026-04-24",
  },
  {
    code: "A2",
    title: "Disruption & incumbents",
    prompt:
      "Why do well-managed incumbents fail in the face of disruptive innovation — and is the failure avoidable? Ground your argument in a specific industry.",
    dueDate: "2026-05-15",
  },
  {
    code: "A3",
    title: "Venture scaling",
    prompt:
      "Premature scaling is often cited as the leading cause of startup death. When is aggressive scaling nevertheless the right strategy?",
    dueDate: "2026-06-05",
  },
];

/** Persona archetype driving each student's transcript-generation profile. */
export type Persona =
  | "independent-strong"
  | "scaffolded-achiever"
  | "developing"
  | "improver"
  | "contrarian"
  | "steady-mid";

export interface StudentDef {
  firstName: string;
  lastName: string;
  persona: Persona;
}

// 40 names spanning a realistic international MBA cohort: East Asian (3),
// South Asian (4), Southeast Asian (5), European (8), African (5), Middle
// Eastern (5), Latin American (5), Anglo (5).
const NAMES: Array<[string, string]> = [
  ["Wei", "Chen"],
  ["Yuki", "Tanaka"],
  ["Min-jun", "Kim"],
  ["Priya", "Sharma"],
  ["Arjun", "Mehta"],
  ["Ayesha", "Khan"],
  ["Nadia", "Rahman"],
  ["Linh", "Nguyen"],
  ["Somchai", "Suwannarat"],
  ["Putri", "Wulandari"],
  ["Miguel", "Santos"],
  ["Aisyah", "Rahman"],
  ["James", "Whitfield"],
  ["Lukas", "Schmidt"],
  ["Camille", "Dubois"],
  ["Giulia", "Romano"],
  ["Carlos", "Fernandez"],
  ["Anna", "Kowalski"],
  ["Erik", "Lindqvist"],
  ["Sofia", "Papadopoulos"],
  ["Chidi", "Okafor"],
  ["Wanjiru", "Kamau"],
  ["Thabo", "Nkosi"],
  ["Kwame", "Asante"],
  ["Youssef", "El-Sayed"],
  ["Layla", "Haddad"],
  ["Omar", "Al-Farsi"],
  ["Reza", "Hosseini"],
  ["Deniz", "Yildiz"],
  ["Fatima", "Al-Sayed"],
  ["Mariana", "Silva"],
  ["Diego", "Hernandez"],
  ["Valentina", "Torres"],
  ["Santiago", "Gomez"],
  ["Camila", "Rojas"],
  ["Emily", "Carter"],
  ["Jack", "Thompson"],
  ["Olivia", "Bennett"],
  ["Ryan", "Mitchell"],
  ["Sarah", "Wilson"],
];

// Persona sequence, tuned so the cohort totals are:
//   independent-strong 8, scaffolded-achiever 6, developing 12,
//   improver 5, contrarian 5, steady-mid 4  (sums to 40)
const PERSONA_SEQUENCE: Persona[] = [
  "independent-strong", // 0
  "developing", // 1
  "scaffolded-achiever", // 2
  "developing", // 3
  "steady-mid", // 4
  "contrarian", // 5
  "developing", // 6
  "independent-strong", // 7
  "developing", // 8
  "improver", // 9
  "scaffolded-achiever", // 10
  "developing", // 11
  "independent-strong", // 12
  "contrarian", // 13
  "developing", // 14
  "scaffolded-achiever", // 15
  "scaffolded-achiever", // 16
  "steady-mid", // 17
  "independent-strong", // 18
  "developing", // 19
  "improver", // 20
  "developing", // 21
  "contrarian", // 22
  "independent-strong", // 23
  "scaffolded-achiever", // 24
  "developing", // 25
  "steady-mid", // 26
  "improver", // 27
  "independent-strong", // 28
  "improver", // 29
  "developing", // 30
  "contrarian", // 31
  "scaffolded-achiever", // 32
  "developing", // 33
  "independent-strong", // 34
  "steady-mid", // 35
  "developing", // 36
  "improver", // 37
  "contrarian", // 38
  "independent-strong", // 39
];

export const STUDENTS: StudentDef[] = NAMES.map(([firstName, lastName], i) => ({
  firstName,
  lastName,
  persona: PERSONA_SEQUENCE[i],
}));

export function studentEmail(firstName: string, lastName: string, index: number): string {
  const norm = (s: string) =>
    s
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-zA-Z]/g, "")
      .toLowerCase();
  return `${norm(firstName)}.${norm(lastName)}${index + 1}@jbs.cam.ac.uk`;
}

/** Student indices (0-based) who have not yet started/completed A3. */
export const SKIP_A3_INDICES = new Set([3, 8, 11, 14, 19, 22, 25, 30, 33, 36]);
