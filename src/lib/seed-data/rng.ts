// Deterministic PRNG utilities for the demo seed. No Math.random, no
// Date.now()-based variation anywhere in the seed data path — every number,
// pick, and shuffle here is a pure function of an integer seed so the demo
// cohort is byte-for-byte reproducible across runs.

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function random(): number {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Simple string -> 32bit int hash (djb2 variant), used to derive seeds. */
export function seedFromString(s: string): number {
  let h = 1779033703 ^ s.length;
  for (let i = 0; i < s.length; i++) {
    h = Math.imul(h ^ s.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  h = Math.imul(h ^ (h >>> 16), 2246822507);
  h = Math.imul(h ^ (h >>> 13), 3266489909);
  return (h ^= h >>> 16) >>> 0;
}

export class Rng {
  private rand: () => number;
  constructor(seed: number) {
    this.rand = mulberry32(seed);
  }
  /** Uniform float in [0, 1). */
  next(): number {
    return this.rand();
  }
  /** Uniform integer in [minIncl, maxIncl]. */
  int(minIncl: number, maxIncl: number): number {
    return minIncl + Math.floor(this.next() * (maxIncl - minIncl + 1));
  }
  pick<T>(arr: readonly T[]): T {
    return arr[this.int(0, arr.length - 1)];
  }
  /** True with probability p (0-1). */
  chance(p: number): boolean {
    return this.next() < p;
  }
}

export function rngFor(...parts: Array<string | number>): Rng {
  return new Rng(seedFromString(parts.join("::")));
}
