import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";

// SQLite persistence. The database file lives in data/ (gitignored) and is
// created + seeded on first access, so `npm run dev` works with zero setup.

const DATA_DIR = path.join(process.cwd(), "data");
const DB_PATH = process.env.COGNITIVEOS_DB_PATH ?? path.join(DATA_DIR, "cognitiveos.db");

declare global {
  // eslint-disable-next-line no-var
  var __cognitiveosDb: Database.Database | undefined;
}

const SCHEMA = `
CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  title TEXT NOT NULL,
  term TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assignments (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  code TEXT NOT NULL,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  due_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS students (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  cohort TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL REFERENCES students(id),
  assignment_id TEXT NOT NULL REFERENCES assignments(id),
  status TEXT NOT NULL DEFAULT 'active',
  started_at TEXT NOT NULL,
  ended_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  tag TEXT,
  quick_action TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE TABLE IF NOT EXISTS turn_analyses (
  message_id TEXT PRIMARY KEY REFERENCES messages(id),
  session_id TEXT NOT NULL REFERENCES sessions(id),
  moves_json TEXT NOT NULL,
  challenge_response TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_session ON turn_analyses(session_id);
CREATE TABLE IF NOT EXISTS milestones (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  kind TEXT NOT NULL,
  label TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_milestones_session ON milestones(session_id, created_at);
CREATE TABLE IF NOT EXISTS session_scores (
  session_id TEXT PRIMARY KEY REFERENCES sessions(id),
  dimensions_json TEXT NOT NULL,
  frameworks_json TEXT NOT NULL,
  independence_index REAL NOT NULL,
  independence_components_json TEXT NOT NULL,
  depth_score REAL NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS faculty_reviews (
  session_id TEXT PRIMARY KEY REFERENCES sessions(id),
  reviewer_name TEXT NOT NULL,
  dimensions_json TEXT NOT NULL,
  comments TEXT NOT NULL,
  created_at TEXT NOT NULL
);
`;

export function getDb(): Database.Database {
  if (globalThis.__cognitiveosDb) return globalThis.__cognitiveosDb;

  fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
  const db = new Database(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(SCHEMA);
  globalThis.__cognitiveosDb = db;

  const count = db.prepare("SELECT COUNT(*) AS n FROM students").get() as { n: number };
  if (count.n === 0) {
    // Lazy import avoids a require cycle (seed uses repo helpers that use getDb)
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { seedDatabase } = require("./seed") as typeof import("./seed");
    seedDatabase(db);
  }

  return db;
}

export function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "").slice(0, 20)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}
