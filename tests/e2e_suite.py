#!/usr/bin/env python
"""End-to-end reliability suite (network + LLM — NOT run by pytest).

Runs the 13-item matrix from the reliability plan sequentially against the
live CLI, prints one PASS/FAIL line per item with tier/latency/tokens,
writes validation/e2e_results.json, and exits non-zero on any FAIL.

Usage:
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers .venv/bin/python tests/e2e_suite.py

The site-profile cache is cleared at start so discovery is exercised;
item 1 additionally verifies cache replay.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Optional

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = os.path.join(REPO, "data", "site_profiles.json")
RESULTS = os.path.join(REPO, "validation", "e2e_results.json")
PY = os.path.join(REPO, ".venv", "bin", "python")

ENV = dict(os.environ)
ENV.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")


def run_cli(args: list[str], timeout: int = 300) -> tuple[Optional[dict], int, str]:
    """Invoke the CLI, return (parsed_json_or_None, exit_code, raw_stdout)."""
    proc = subprocess.run([PY, "-m", "webaccess.cli", *args],
                          cwd=REPO, env=ENV, capture_output=True, text=True,
                          timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = None
    return data, proc.returncode, proc.stdout


def _metrics(d: Optional[dict]) -> tuple[Any, Any, Any]:
    if not d:
        return None, None, None
    return d.get("tier_used"), round(d.get("latency_s") or 0, 1), d.get("tokens_used")


# --- individual items ------------------------------------------------------
# Each returns (passed: bool, detail: str, tier, latency, tokens).

def item_1_tier0_url_and_cache():
    d, code, _ = run_cli(["--url", "https://job-boards.greenhouse.io/gitlab",
                          "--kind", "jobs", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    if not d:
        return False, "no JSON", tier, lat, tok
    n = len(d.get("data") or [])
    ok = (tier == 0 and n > 100 and (d.get("latency_s") or 99) < 10
          and tok == 0 and code == 0)
    detail = f"tier0 count={n} latency={lat} tokens={tok}"
    if not ok:
        return False, detail, tier, lat, tok
    # cache replay: second run WITHOUT --no-cache must hit the cached recipe
    d2, _, _ = run_cli(["--url", "https://job-boards.greenhouse.io/gitlab",
                        "--kind", "jobs", "--compact"], timeout=120)
    method = (d2 or {}).get("method") or ""
    if not method.endswith("(cached)"):
        return False, detail + f" | cache replay method={method!r}", tier, lat, tok
    return True, detail + f" | cached method={method}", tier, lat, tok


def item_2_slug_probe():
    d, code, _ = run_cli(["--url", "https://stripe.com/jobs/search",
                          "--kind", "jobs", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    n = len(d.get("data") or []) if d else 0
    ok = bool(d) and tier == 0 and n > 400 and tok == 0 and code == 0
    return ok, f"tier{tier} count={n} tokens={tok}", tier, lat, tok


def item_3_lever():
    d, code, _ = run_cli(["--url", "https://jobs.lever.co/palantir",
                          "--kind", "jobs", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    n = len(d.get("data") or []) if d else 0
    ok = bool(d) and tier == 0 and n > 200 and code == 0
    return ok, f"tier{tier} count={n}", tier, lat, tok


def item_4_spa_fields():
    d, code, _ = run_cli(["--url", "https://quotes.toscrape.com/js/",
                          "--kind", "fields", "--fields",
                          "first_quote_author,total_quotes_on_page",
                          "--no-cache", "--compact"], timeout=600)
    tier, lat, tok = _metrics(d)
    data = (d or {}).get("data") or {}
    author = str(data.get("first_quote_author") or "")
    total = str(data.get("total_quotes_on_page") or "")
    ok = (bool(d) and d.get("success") and tier == 2
          and "einstein" in author.lower() and "10" in total)
    return ok, f"tier{tier} author={author!r} total={total!r}", tier, lat, tok


def item_5_static_page_info():
    d, code, _ = run_cli(["--url", "https://www.python.org/about/",
                          "--kind", "page_info", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    ok = (bool(d) and d.get("success") and (tier is not None and tier <= 1)
          and tok == 0)
    return ok, f"tier{tier} tokens={tok}", tier, lat, tok


def item_6_fields_escalation():
    d, code, _ = run_cli(["--url", "https://www.anthropic.com/pricing",
                          "--kind", "fields", "--fields",
                          "cheapest_paid_plan_name,cheapest_paid_plan_price",
                          "--no-cache", "--compact"], timeout=600)
    tier, lat, tok = _metrics(d)
    data = (d or {}).get("data") or {}
    name = data.get("cheapest_paid_plan_name")
    price = data.get("cheapest_paid_plan_price")
    ok = bool(d) and d.get("success") and name not in (None, "") and price not in (None, "")
    return ok, f"tier{tier} name={name!r} price={price!r}", tier, lat, tok


def item_7_guardrail_robots():
    d, code, _ = run_cli(["--url", "https://www.linkedin.com/jobs/search",
                          "--kind", "jobs", "--compact"], timeout=60)
    tier, lat, tok = _metrics(d)
    attempts = len((d or {}).get("attempts") or []) if d and "attempts" in d else 0
    ok = (bool(d) and d.get("status") == "blocked_robots"
          and d.get("success") is False and code == 0)
    return ok, f"status={d.get('status') if d else None} exit={code}", tier, lat, tok


def item_8_guardrail_auth():
    d, code, _ = run_cli(["--url", "https://www.figma.com/files/recent",
                          "--kind", "page_info", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    ok = bool(d) and d.get("status") == "auth_required" and code == 0
    return ok, f"status={d.get('status') if d else None} exit={code}", tier, lat, tok


def item_9_captcha_false_positive():
    # Live content page that embeds a captcha include (verified separately).
    d, code, _ = run_cli(["--url", CAPTCHA_PAGE,
                          "--kind", "page_info", "--no-cache", "--compact"], timeout=600)
    tier, lat, tok = _metrics(d)
    ok = (bool(d) and d.get("success") and d.get("status") != "auth_required")
    return ok, f"{CAPTCHA_PAGE} status={d.get('status') if d else None}", tier, lat, tok


def item_10_embed_crosstalk_offline():
    # Offline logic regression (network-free): a blog merely linking another
    # company's board must NOT yield that company's ATS token.
    sys.path.insert(0, REPO)
    from webaccess.tier0_structured import detect_ats
    blog = '<article>See <a href="https://jobs.lever.co/palantir">Palantir</a></article>'
    got = detect_ats("https://someblog.example.com/post", blog)
    embed = '<script>fetch("https://api.lever.co/v0/postings/realco?mode=json")</script>'
    got2 = detect_ats("https://realco.example.com/careers", embed)
    ok = got is None and got2 == ("lever", "realco")
    return ok, f"blog_link={got} embed={got2}", None, 0, 0


def item_11_vision():
    d, code, _ = run_cli(["--url", "https://quotes.toscrape.com/js/",
                          "--kind", "fields", "--fields", "first_quote_author",
                          "--min-tier", "4", "--no-cache", "--compact"], timeout=600)
    tier, lat, tok = _metrics(d)
    data = (d or {}).get("data") or {}
    author = str(data.get("first_quote_author") or "")
    ok = bool(d) and tier == 4 and "einstein" in author.lower()
    return ok, f"tier{tier} author={author!r}", tier, lat, tok


def item_12_unreachable():
    d, code, _ = run_cli(["--url", "https://definitely-not-a-real-domain-xq81.com/x",
                          "--kind", "page_info", "--no-cache", "--compact"], timeout=120)
    tier, lat, tok = _metrics(d)
    ok = bool(d) and d.get("status") == "unreachable" and code == 1
    return ok, f"status={d.get('status') if d else None} exit={code}", tier, lat, tok


def item_13_crash_safety():
    d, code, raw = run_cli(["--url", "notaurl", "--kind", "page_info", "--compact"],
                           timeout=60)
    has_traceback = "Traceback (most recent call last)" in raw
    ok = (bool(d) and d.get("status") == "error" and code == 2
          and not has_traceback)
    return ok, f"status={d.get('status') if d else None} exit={code} traceback={has_traceback}", None, 0, 0


# A public, content-rich page that genuinely ships a reCAPTCHA include
# (verified: "recaptcha" in first 20k chars, ~1200 visible words). Before
# the P0-1 fix this tripped looks_like_auth_wall; it must now succeed.
CAPTCHA_PAGE = "https://developers.google.com/recaptcha/docs/display"

ITEMS = [
    ("1_tier0_url_and_cache", item_1_tier0_url_and_cache),
    ("2_slug_probe", item_2_slug_probe),
    ("3_lever", item_3_lever),
    ("4_spa_fields", item_4_spa_fields),
    ("5_static_page_info", item_5_static_page_info),
    ("6_fields_escalation", item_6_fields_escalation),
    ("7_guardrail_robots", item_7_guardrail_robots),
    ("8_guardrail_auth", item_8_guardrail_auth),
    ("9_captcha_false_positive", item_9_captcha_false_positive),
    ("10_embed_crosstalk_offline", item_10_embed_crosstalk_offline),
    ("11_vision", item_11_vision),
    ("12_unreachable", item_12_unreachable),
    ("13_crash_safety", item_13_crash_safety),
]


def clear_cache() -> None:
    if os.path.exists(PROFILES):
        os.remove(PROFILES)


def main() -> int:
    clear_cache()
    print(f"e2e suite — {len(ITEMS)} items — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    results = []
    all_pass = True
    for name, fn in ITEMS:
        t0 = time.monotonic()
        retried = False
        try:
            passed, detail, tier, lat, tok = fn()
            if not passed:
                # one retry for network/LLM flakiness
                retried = True
                passed, detail, tier, lat, tok = fn()
        except Exception as e:
            passed, detail, tier, lat, tok = False, f"EXC {type(e).__name__}: {e}", None, None, None
        wall = round(time.monotonic() - t0, 1)
        status = "PASS" if passed else "FAIL"
        all_pass = all_pass and passed
        rmark = " (retried)" if retried else ""
        print(f"{status}  {name:30s} tier={tier} latency={lat} tokens={tok} "
              f"wall={wall}s{rmark}  {detail}")
        results.append({"name": name, "passed": passed, "tier": tier,
                        "latency_s": lat, "tokens": tok, "wall_s": wall,
                        "retried": retried, "detail": detail})

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w") as f:
        json.dump({"ts": time.time(), "all_pass": all_pass, "results": results},
                  f, indent=2)
    n_pass = sum(1 for r in results if r["passed"])
    print(f"\n{n_pass}/{len(ITEMS)} PASS  ->  {RESULTS}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
