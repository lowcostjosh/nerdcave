# Web-Access Playbook: the tiered decision tree

**TL;DR: never start with a screenshot.** Most "browse this website" tasks
resolve with a plain HTTP request or a public API the site already
publishes — for free, in seconds, with zero LLM tokens. This repo ships a
router (`webaccess/`) that enforces that discipline mechanically, plus a
Claude Code Skill (`.claude/skills/web-extraction/`) so future sessions
apply it automatically.

## The decision tree (plain language)

```
Given (url, task):
│
├─ Seen this site+task before? ──────────────► replay cached recipe
│     (re-validated on every use; stale recipes fail loudly and
│      re-enter discovery — never silently return wrong data)
│
├─ TIER 0 — data the site already publishes, structured
│     ATS job APIs: Greenhouse / Lever / Ashby (public, no auth),
│     detected from the URL or from embeds inside custom careers pages;
│     schema.org JSON-LD; RSS/Atom; sitemap.xml; llms.txt.
│     Free, complete, exact. ALWAYS checked first.
│
├─ TIER 1 — static HTML, no JS execution
│     robots.txt check → httpx GET (retries+backoff, per-domain rate
│     limit, in-run cache) → auth-wall / CAPTCHA detection → JS-shell
│     detection. Interpretation: trafilatura (no LLM) for content pages;
│     haiku over static text when the task needs interpretation.
│     Follows rel-next pagination (bounded).
│
├─ TIER 2 — rendered DOM / accessibility tree (no pixels)
│     Playwright, full-Chromium, aria snapshot. Bounded "load more"
│     clicking + infinite-scroll expansion, reported in the result.
│     Interpretation: JSON-LD from rendered HTML (code), else haiku on
│     the aria snapshot.
│
├─ TIER 3 — LLM-planned interaction (Stagehand-style act/observe)
│     Reserved for multi-step ambiguous flows; read-only extraction
│     almost never needs it (validated: 0 of our test sites did).
│
└─ TIER 4 — vision/screenshots. LAST RESORT.
      Canvas/WebGL UI, or tiers 0-2 all measurably failed.

Model ladder (independent of the tiers above):
  no LLM at all  →  haiku  →  sonnet
  Escalate the model only when the cheaper model's output fails schema
  validation. tier_used and model_used are reported separately.

Terminal statuses: auth_required (login wall/paywall/CAPTCHA — reported,
NEVER bypassed), blocked_robots (respected), no_data, unreachable.
```

## Why this ordering — measured, not assumed

One page, three ways (GitLab careers, 145 postings, same machine):

| Approach | Result | Latency | LLM tokens |
|---|---|---|---|
| Tier 0 (Greenhouse API, auto-detected) | 145/145 jobs, all fields exact | **1.5 s** | **0** |
| Tier 1 forced (static HTML + haiku) | 49/145 jobs (page-1 truncation*), no URLs | 144 s | 41k |
| Tier 4 (vision) | never needed | — | — |

\* before pagination-following was added; it now follows rel-next up to 5
pages. The point stands: the API is two orders of magnitude better on
every axis, and a screenshot pipeline would have been worse still.

Validation results across the full site mix: see
`validation/*.json` and the summary table below.

## Tool comparison (recon + hands-on where testable)

| Tool | License | Default mode | DOM-only possible? | Plan caching | Needs own LLM key | Runs here | Verdict for this pipeline |
|---|---|---|---|---|---|---|---|
| **httpx + selectolax + trafilatura** (chosen core, Tiers 0–1) | BSD/MIT/Apache | static HTML | n/a (no LLM) | via our recipe cache | no | ✅ tested | Fastest, zero-token baseline; trafilatura F1≈0.86 on articles |
| **Playwright (library)** (chosen core, Tier 2/4) | Apache-2.0 | DOM + aria snapshot | yes (`aria_snapshot()`) | via our recipe cache | no | ✅ tested | The right substrate; a11y snapshot is compact and LLM-friendly |
| **crawl4ai** 0.9.0 | Apache-2.0 | DOM-first, markdown out | yes (`JsonCssExtractionStrategy`, no LLM) | no plan replay | optional | ✅ tested | Excellent Tier-1/2 alternative; heavier output (17k chars vs our 1.5k on same page), ~2x our static latency, wins on JS pages it renders in one call. Good for bulk crawls |
| **playwright-mcp** v0.0.77 | Apache-2.0 | a11y snapshot ("snapshot mode") | yes (default) | no | no | ✅ (as MCP) | Right idea, wrong economics for a coding agent: streams full a11y tree per step (~114k tokens/task measured by MS) |
| **@playwright/cli + Skills** v0.1.15 | Apache-2.0 | bash-driven, output to disk | yes | n/a | no | ✅ | ~4x cheaper than MCP (~27k tokens/task); validates our bash-invocable-script packaging. Still pre-1.0 |
| **Stagehand** v3 (TS first, Python official) | MIT | hybrid a11y + screenshots | partially (DOM agent mode) | yes: observe/act cache + self-heal | **yes** | ❌ no key in env | Best-in-class for Tier 3 *actions*; adopt if/when multi-step flows are needed and a key exists |
| **browser-use** v0.13 | MIT | vision "auto" + DOM blend | yes (`use_vision=False`) | cloud only (OSS: no replay) | **yes** | ❌ no key in env | Popular but works against DOM-first defaults out of the box; 41-dep install |
| **Firecrawl** v2.x | AGPL-3.0 (SDKs MIT) | cloud API, markdown/JSON | JSON mode requires LLM | 2-day URL cache | yes (cloud key) | ❌ | Practical product is the paid cloud; self-host lacks core features. Skip |
| **Skyvern** v1.x | AGPL-3.0 | **vision-first** | no | yes (learn-replay) | yes | ❌ | Vision-first + advertises CAPTCHA solving/proxy evasion → excluded on guardrails |
| **chrome-devtools-mcp** v1.5 | Apache-2.0 | CDP debugging (a11y snapshots) | yes | no | no | ✅ (as MCP) | For perf/debugging, not extraction. Complementary |
| **AgentQL / LaVague / ScrapeGraphAI / llm-scraper** | various | DOM+LLM | varies | varies | yes | ❌ | Niche or key-gated; trafilatura+haiku covers their use here |

**Recommendation:** core = stdlib HTTP + trafilatura + Playwright aria +
`claude -p` (haiku-first), exactly as shipped. crawl4ai as the bulk-crawl
alternative. Stagehand is the one to add for interactive Tier-3 flows
later. Nothing vision-first earns a default slot.

## Validation summary

_(filled from validation/*.json — see that directory for full diffs)_

| Group | Sites | Outcome |
|---|---|---|
| Greenhouse/Lever (Tier 0 + forced page-extraction diff vs API) | pending | pending |
| Custom careers (no ATS API) | pending | pending |
| JS-heavy SPAs | pending | pending |
| General pages + guardrails | pending | pending |

## Guardrails (defaults, not options)

- robots.txt respected before any fetch; per-domain rate limit (1 req/s);
  in-run URL cache.
- Login walls, paywalls, CAPTCHAs → `auth_required`, reported clearly.
  No bypass, no CAPTCHA solving, no anti-bot evasion — tools that sell
  those features were excluded from defaults.
- Official/public APIs and published structured data preferred over
  reverse-engineering private endpoints (the ATS APIs used are the
  vendors' documented public job-board APIs).
- Every extraction is schema-validated (pydantic) before being trusted;
  every attempt is logged to `data/run_log.jsonl` (tier, model, latency,
  tokens) so tier ordering keeps improving from evidence.

## Environment notes (Claude Code remote containers)

- `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`; pin `playwright==1.56.0`
  (matches pre-installed Chromium 1194; do not run `playwright install`).
- The egress proxy resets Chromium's TLS 1.3 ClientHello. Fix (already in
  `tier2_rendered.py`): pass `--ssl-version-max=tls1.2` and use the full
  Chromium binary at `/opt/pw-browsers/chromium` — the headless-shell
  build fails even with the flag. The proxy re-terminates TLS itself, so
  the 1.2 cap on the browser→proxy leg sacrifices nothing.
- LLM calls shell out to `claude -p --model haiku --output-format json`;
  token accounting includes cache-creation (~24k/call CLI overhead) —
  real cost, honestly counted.
