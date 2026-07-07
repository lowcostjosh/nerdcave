import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CognitiveOS — Reasoning infrastructure for higher education",
  description:
    "Measure how students think, not just what they submit. Socratic AI, reasoning traces, multi-framework scoring, and the Independence Index.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen antialiased`}>
        <header className="border-b border-line bg-card/80 backdrop-blur sticky top-0 z-40">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-lg font-semibold tracking-tight text-ink">
                Cognitive<span className="text-gold">OS</span>
              </span>
              <span className="hidden text-xs text-slate-mid sm:inline">
                reasoning infrastructure for higher education
              </span>
            </Link>
            <nav className="flex items-center gap-1 text-sm">
              <Link
                href="/student"
                className="rounded-md px-3 py-1.5 text-ink-soft transition hover:bg-cream-deep hover:text-ink"
              >
                Student
              </Link>
              <Link
                href="/faculty"
                className="rounded-md px-3 py-1.5 text-ink-soft transition hover:bg-cream-deep hover:text-ink"
              >
                Faculty
              </Link>
            </nav>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
