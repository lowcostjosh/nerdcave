---
name: web-extraction
description: >
  Get information from any website the cheap, reliable way: a tiered router
  that tries published structured data (ATS APIs, JSON-LD, feeds) first,
  then static HTML, then rendered DOM/accessibility tree, and uses
  screenshots/vision only as a last resort. Use whenever the task involves
  extracting data from a URL or website — job postings, pricing, contact
  info, page content, "what does this site say about X" — or checking many
  pages of the same site. Do NOT hand-roll Playwright/screenshot flows or
  reach for vision first; run this router instead. Handles robots.txt,
  rate limiting, pagination, login-wall detection, and caches a per-site
  recipe so repeat visits skip discovery.
---

# Tiered web extraction

## When to use

Any "get info from / check a website" task: job boards, careers pages,
pricing/about/contact pages, JS-heavy SPAs, answering a question from a
page. For multi-step *interactions* (filling forms, logging in), this
skill's read-only router does not apply — but its ladder still tells you
where to start (accessibility tree, not screenshots).

## How to run it

From the repo root (`webaccess/` package must be importable; a venv with
`requirements.txt` installed lives at `.venv/` — create it with
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` if missing):

```bash
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers .venv/bin/python -m webaccess.cli \
  --url "https://example.com/careers" --kind jobs
```

Task kinds:
- `--kind jobs` — returns a JSON list of postings (title, location, company, url, date_posted, salary, department)
- `--kind fields --fields price,contact_email` — returns exactly those keys
- `--kind page_info --question "What does this company sell?"` — title/summary/facts

The output JSON tells you what happened: `tier_used` (0 structured API /
1 static HTML / 2 rendered DOM / 4 vision), `model_used` (null = no LLM
call at all), `latency_s`, `tokens_used`, `status`, and the full `attempts`
ladder. Long runs (LLM tiers) can take minutes — use a generous Bash timeout.

## The decision ladder (what the router does for you)

1. **Tier 0 — published structured data.** Greenhouse/Lever/Ashby public
   job APIs (detected from the URL *or* from embeds inside a custom page),
   schema.org JSON-LD, RSS/sitemap/llms.txt. Free, complete, exact. This
   resolves more sites than you'd expect — always let it try first.
2. **Tier 1 — static HTML.** httpx + trafilatura (no LLM) for content
   pages; haiku over the static text when interpretation is needed.
   Follows rel-next pagination (bounded at 5 pages).
3. **Tier 2 — rendered DOM.** Playwright accessibility snapshot (no
   pixels), with bounded load-more clicking and infinite-scroll expansion.
   For JS shells only — the router detects those automatically.
4. **Tier 4 — vision.** Screenshot + model. Last resort only (canvas/WebGL
   UI or everything else measurably failed).

The **model ladder is independent**: no-LLM -> haiku -> sonnet, escalating
only when validation fails. Never start with a big model on a page a
parser can read.

## Statuses you must respect

- `auth_required` — login wall / paywall / CAPTCHA. Report it to the user;
  never attempt bypass or CAPTCHA solving.
- `blocked_robots` — robots.txt disallows. Respect it; tell the user.
- `no_data` / `unreachable` — reachable-but-empty vs network failure;
  both come with the attempt ladder for diagnosis.
- `error` — malformed input or an unexpected pipeline failure. The CLI
  always still prints a valid result JSON (never a bare traceback).

**Exit codes:** `0` = success or a clean refusal (`auth_required`,
`blocked_robots`); `1` = `unreachable` / `no_data`; `2` = `error`
(invalid URL or pipeline exception). Always parse stdout JSON regardless.

## The site-profile cache

`data/site_profiles.json` remembers which recipe worked per site+task
(e.g. "this careers page is Greenhouse token acme behind an embed").
Repeat runs skip discovery. Recipes are re-validated on every use and
invalidated loudly (`stale_reason`) when a site changes — discovery then
re-runs automatically. Don't delete the file; it's the pipeline's memory.
`--no-cache` forces fresh discovery; `--min-tier N` skips cheaper tiers
(testing/validation only).

## Library use (from Python)

```python
from webaccess import Router, Task
result = Router().run("https://jobs.lever.co/palantir", Task(kind="jobs"))
result.tier_used, result.tokens_used, len(result.data)
```

## Environment notes (Claude Code remote containers)

- Always set `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`; keep
  `playwright==1.56.0` (matches the pre-installed Chromium — do NOT run
  `playwright install`).
- The egress proxy resets Chromium TLS 1.3 ClientHellos; the renderer
  already passes `--ssl-version-max=tls1.2` and uses the full Chromium
  binary (`/opt/pw-browsers/chromium`), not the headless shell. If you
  write your own Playwright scripts, do the same.
- LLM tiers shell out to `claude -p --model haiku` — no API key needed.

See `playbook.md` at the repo root for the full decision tree, tool
comparison, and validation numbers behind these defaults.
