// Shared color-scale utilities for the faculty dashboard's charts.
// All colors are drawn from the CognitiveOS tokens registered in globals.css
// (cream / ink / gold / teal / brick) — this file only computes *interpolation*
// and *contrast*, it never introduces a new hue.
import type { TrendDirection } from "@/lib/types";

const INK = "#202b3c";
const CREAM = "#f6f3ec";

// ---------- WCAG contrast (used to pick readable text on a filled cell) ----------

function srgbToLin(c: number): number {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const bigint = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

function relLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex);
  return 0.2126 * srgbToLin(r) + 0.7152 * srgbToLin(g) + 0.0722 * srgbToLin(b);
}

export function contrastRatio(hexA: string, hexB: string): number {
  const la = relLuminance(hexA);
  const lb = relLuminance(hexB);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

/** Pick ink or cream text — whichever contrasts better against the given background. */
export function pickTextColor(bgHex: string): string {
  return contrastRatio(bgHex, INK) >= contrastRatio(bgHex, CREAM) ? INK : CREAM;
}

// ---------- Sequential ramp for the heatmap (0-4 scale) ----------
// Low = pale warm (needs teaching), mid = neutral gold, high = deep teal
// (strengthening). Three-stop piecewise interpolation in RGB space.

const HEATMAP_STOPS: Array<{ t: number; hex: string }> = [
  { t: 0, hex: "#f6e4de" }, // brick-soft
  { t: 0.32, hex: "#f3e9d2" }, // gold-soft
  { t: 0.66, hex: "#cfe0da" }, // teal-soft (deepened slightly for mid-high)
  { t: 1, hex: "#3e6d64" }, // teal
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpHex(hexA: string, hexB: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(hexA);
  const [r2, g2, b2] = hexToRgb(hexB);
  const r = Math.round(lerp(r1, r2, t));
  const g = Math.round(lerp(g1, g2, t));
  const b = Math.round(lerp(b1, b2, t));
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

/** mean is 0-4 (or null for no data). Returns a background hex + a readable text hex. */
export function heatmapCellColor(mean: number | null): { bg: string; fg: string } {
  if (mean === null) {
    return { bg: "#f3f1ea", fg: "#8b8a84" };
  }
  const t = Math.min(1, Math.max(0, mean / 4));
  let bg: string;
  if (t <= HEATMAP_STOPS[1].t) {
    const local = t / HEATMAP_STOPS[1].t;
    bg = lerpHex(HEATMAP_STOPS[0].hex, HEATMAP_STOPS[1].hex, local);
  } else if (t <= HEATMAP_STOPS[2].t) {
    const local = (t - HEATMAP_STOPS[1].t) / (HEATMAP_STOPS[2].t - HEATMAP_STOPS[1].t);
    bg = lerpHex(HEATMAP_STOPS[1].hex, HEATMAP_STOPS[2].hex, local);
  } else {
    const local = (t - HEATMAP_STOPS[2].t) / (1 - HEATMAP_STOPS[2].t);
    bg = lerpHex(HEATMAP_STOPS[2].hex, HEATMAP_STOPS[3].hex, local);
  }
  return { bg, fg: pickTextColor(bg) };
}

// ---------- Trend direction chips ----------

export function trendChipStyle(direction: TrendDirection): {
  bg: string;
  fg: string;
  label: string;
} {
  switch (direction) {
    case "improving":
    case "rising":
      return { bg: "var(--color-teal-soft)", fg: "var(--color-teal)", label: humanizeTrend(direction) };
    case "stuck":
    case "declining":
      return { bg: "var(--color-brick-soft)", fg: "var(--color-brick)", label: humanizeTrend(direction) };
    case "stable":
    default:
      return { bg: "var(--color-cream-deep)", fg: "var(--color-ink-soft)", label: humanizeTrend(direction) };
  }
}

function humanizeTrend(direction: TrendDirection): string {
  return direction.charAt(0).toUpperCase() + direction.slice(1);
}

// ---------- Scatter categories ----------

export type ScatterCategory = "dependency" | "belowBoth" | "exemplar" | "other";

export const SCATTER_CATEGORY_COLOR: Record<ScatterCategory, string> = {
  dependency: "var(--color-brick)",
  belowBoth: "var(--color-gold)",
  exemplar: "var(--color-teal)",
  other: "var(--color-ink)",
};

export const SCATTER_CATEGORY_LABEL: Record<ScatterCategory, string> = {
  dependency: "Dependency pattern",
  belowBoth: "Below both thresholds",
  exemplar: "Exemplar",
  other: "Other students",
};

// ---------- Diverging (validity r) ----------

/** r in [-1, 1]. Returns a fill proportional to |r|, teal for positive, brick for negative. */
export function validityBarColor(r: number): string {
  return r >= 0 ? "var(--color-teal)" : "var(--color-brick)";
}

// ---------- Generic text humanizer ----------

export function humanizeKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
