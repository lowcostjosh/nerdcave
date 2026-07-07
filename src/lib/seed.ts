import type { Database } from "better-sqlite3";
import { newId } from "./db";

// STUB — replaced by the full demo-cohort generator.
// Seeds the minimum data needed for the app to boot.

export function seedDatabase(db: Database): void {
  const courseId = newId("course");
  db.prepare("INSERT INTO courses (id, code, title, term) VALUES (?, ?, ?, ?)").run(
    courseId,
    "MBA35C",
    "Entrepreneurship",
    "Easter 2026"
  );
  db.prepare(
    "INSERT INTO assignments (id, course_id, code, title, prompt, due_date) VALUES (?, ?, ?, ?, ?, ?)"
  ).run(
    newId("asgn"),
    courseId,
    "A1",
    "Platform competition",
    "Is a first-mover advantage in digital platform markets sustainable? Take a position and defend it.",
    "2026-05-01"
  );
  db.prepare("INSERT INTO students (id, name, email, cohort) VALUES (?, ?, ?, ?)").run(
    newId("stu"),
    "Demo Student",
    "demo@jbs.cam.ac.uk",
    "MBA 2026"
  );
}
