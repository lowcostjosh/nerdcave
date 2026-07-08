"""Tier 0: data the site already publishes in structured form.

Checked first, always: ATS job APIs (Greenhouse, Lever, Ashby),
schema.org JSON-LD, RSS/Atom feeds, sitemap.xml, llms.txt.
No LLM, no browser.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlparse

from selectolax.parser import HTMLParser

from .fetch import FETCHER, FetchResponse
from .types import JobPosting

# --- ATS detection -------------------------------------------------------

ATS_URL_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.(?:eu\.)?greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_-]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)")),
]

# STRONG embed evidence: the page actually hosts/mounts the ATS's own
# board or apply widget for a specific token. Trustworthy on its own —
# a blog can *link* an ATS board, but it does not embed the widget config.
ATS_STRONG_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.(?:eu\.)?greenhouse\.io/embed/job_(?:board|app)\?(?:[^\"'\s]*&)?for=([A-Za-z0-9_-]+)")),
    ("greenhouse", re.compile(r"(?:grnhse|Grnhse)\.Iframe[\s\S]{0,300}?for\s*:\s*['\"]([A-Za-z0-9_-]+)['\"]")),
    ("lever", re.compile(r"api\.(?:eu\.)?lever\.co/v0/postings/([A-Za-z0-9_-]+)")),
    ("ashby", re.compile(r"api\.ashbyhq\.com/posting-api/job-board/([A-Za-z0-9_.-]+)")),
]

# WEAK evidence: a mere hyperlink to an ATS board. Any page linking a
# company's board matches this, so a bare match is NOT accepted — it must
# pass the domain-slug or title cross-check in detect_ats.
ATS_WEAK_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.(?:eu\.)?greenhouse\.io/([A-Za-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_-]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.-]+)")),
]

_RESERVED_TOKENS = {"embed", "job_board", "job_app", "v0", "postings",
                    "posting-api", "www"}


def _domain_slug(url: str) -> str:
    parts = urlparse(url).netloc.lower().split(".")
    return parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")


def _titles_confirm(jobs: list[JobPosting], html: str, need: int = 2) -> bool:
    """A slug collision can't survive this: several of the fetched board's
    own job titles must appear verbatim in the page HTML."""
    return sum(1 for j in jobs[:40] if len(j.title) > 8 and j.title in html) >= need


def detect_ats(url: str, html: Optional[str] = None) -> Optional[tuple[str, str]]:
    """Return (platform, board_token) if this URL or page is ATS-backed.

    Confidence-tiered so a page that merely *links* another company's board
    (e.g. a blog citing Palantir's careers) never yields that company's data:
      - URL hosted on the ATS -> accept.
      - STRONG embed (widget config for a token) -> accept.
      - WEAK link -> accept only if the token is this domain's own slug, or
        the same token is linked >=2x AND the board's titles appear verbatim.
    """
    for platform, pat in ATS_URL_PATTERNS:
        m = pat.search(url)
        if m:
            return platform, m.group(1)
    if not html:
        return None

    for platform, pat in ATS_STRONG_PATTERNS:
        m = pat.search(html)
        if m and m.group(1) and m.group(1).lower() not in _RESERVED_TOKENS:
            return platform, m.group(1)

    slug = _domain_slug(url)
    for platform, pat in ATS_WEAK_PATTERNS:
        tokens = [m.group(1) for m in pat.finditer(html)
                  if m.group(1).lower() not in _RESERVED_TOKENS]
        if not tokens:
            continue
        # (a) token equals the page's own domain slug -> self-referential,
        # trustworthy without a network round-trip.
        for t in tokens:
            if t.lower() == slug:
                return platform, t
        # (b) same token linked repeatedly AND the board's titles are on the
        # page -> the page really is this board's front end.
        from collections import Counter
        for t, n in Counter(tokens).most_common():
            if n >= 2:
                jobs = ATS_FETCHERS[platform](t)
                if len(jobs) >= 2 and _titles_confirm(jobs, html):
                    return platform, t
    return None


# --- ATS public APIs (documented, no auth) --------------------------------

def fetch_greenhouse_jobs(token: str) -> list[JobPosting]:
    resp = FETCHER.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=false")
    if not resp.ok:
        return []
    jobs = json.loads(resp.text).get("jobs", [])
    out = []
    for j in jobs:
        out.append(JobPosting(
            title=j.get("title", ""),
            location=(j.get("location") or {}).get("name"),
            company=j.get("company_name") or token,
            url=j.get("absolute_url"),
            date_posted=(j.get("updated_at") or "")[:10] or None,
            department=", ".join(d.get("name", "") for d in j.get("departments") or []) or None,
        ))
    return out


def fetch_lever_jobs(site: str) -> list[JobPosting]:
    resp = FETCHER.get(f"https://api.lever.co/v0/postings/{site}?mode=json")
    if not resp.ok:
        return []
    out = []
    for j in json.loads(resp.text):
        cats = j.get("categories") or {}
        salary = None
        sr = j.get("salaryRange")
        if sr and sr.get("min"):
            salary = f"{sr.get('currency', 'USD')} {sr['min']}-{sr.get('max', '')}"
        created = j.get("createdAt")
        out.append(JobPosting(
            title=j.get("text", ""),
            location=cats.get("location"),
            company=site,
            url=j.get("hostedUrl"),
            date_posted=__import__("datetime").datetime.utcfromtimestamp(created / 1000).strftime("%Y-%m-%d") if created else None,
            salary=salary,
            department=cats.get("team") or cats.get("department"),
        ))
    return out


def fetch_ashby_jobs(org: str) -> list[JobPosting]:
    resp = FETCHER.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true")
    if not resp.ok:
        return []
    try:
        jobs = json.loads(resp.text).get("jobs", [])
    except json.JSONDecodeError:
        return []
    out = []
    for j in jobs:
        comp = j.get("compensation") or {}
        salary = comp.get("compensationTierSummary") or None
        out.append(JobPosting(
            title=j.get("title", ""),
            location=j.get("location"),
            company=org,
            url=j.get("jobUrl") or j.get("applyUrl"),
            date_posted=(j.get("publishedAt") or "")[:10] or None,
            salary=salary,
            department=j.get("department"),
        ))
    return out


ATS_FETCHERS = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
    "ashby": fetch_ashby_jobs,
}


# --- schema.org JSON-LD ----------------------------------------------------

def _iter_jsonld(html: str):
    tree = HTMLParser(html)
    for node in tree.css('script[type="application/ld+json"]'):
        raw = node.text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                yield from (item.get("@graph") if isinstance(item.get("@graph"), list) else [item])


def extract_jsonld_jobs(html: str) -> list[JobPosting]:
    out = []
    for item in _iter_jsonld(html):
        if not isinstance(item, dict) or item.get("@type") not in ("JobPosting", ["JobPosting"]):
            continue
        org = item.get("hiringOrganization") or {}
        loc = item.get("jobLocation")
        loc_name = None
        if isinstance(loc, list) and loc:
            loc = loc[0]
        if isinstance(loc, dict):
            addr = loc.get("address") or {}
            if isinstance(addr, dict):
                loc_name = ", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry") if isinstance(addr.get("addressCountry"), str) else None])) or None
        salary = None
        base = item.get("baseSalary")
        if isinstance(base, dict):
            val = base.get("value")
            if isinstance(val, dict):
                lo, hi = val.get("minValue"), val.get("maxValue")
                if lo or hi or val.get("value"):
                    salary = f"{base.get('currency', '')} {lo or val.get('value', '')}-{hi or ''}".strip(" -")
        out.append(JobPosting(
            title=item.get("title", ""),
            location=loc_name,
            company=org.get("name") if isinstance(org, dict) else None,
            url=item.get("url"),
            date_posted=(item.get("datePosted") or "")[:10] or None,
            salary=salary,
        ))
    return [j for j in out if j.title]


def extract_jsonld_facts(html: str) -> dict[str, Any]:
    """Non-job structured data (Organization, Product, FAQ...)."""
    facts: dict[str, Any] = {}
    for item in _iter_jsonld(html):
        t = item.get("@type")
        if isinstance(t, list):
            t = t[0] if t else None
        if t and t not in facts:
            keep = {k: v for k, v in item.items()
                    if k in ("name", "description", "url", "telephone", "email",
                             "address", "offers", "priceRange", "sameAs") and v}
            if keep:
                facts[t] = keep
    return facts


# --- feeds / sitemap / llms.txt -------------------------------------------

def probe_site_extras(url: str) -> dict[str, Any]:
    """Cheap existence checks for machine-readable site resources."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    extras: dict[str, Any] = {}
    llms = FETCHER.get(f"{base}/llms.txt")
    if llms.ok and llms.status_code == 200 and "<html" not in llms.text[:500].lower():
        extras["llms_txt"] = llms.text[:4000]
    sitemap = FETCHER.get(f"{base}/sitemap.xml")
    if sitemap.ok and ("<urlset" in sitemap.text[:2000] or "<sitemapindex" in sitemap.text[:2000]):
        extras["sitemap"] = f"{base}/sitemap.xml"
    return extras


def find_feeds(html: str, base_url: str) -> list[str]:
    tree = HTMLParser(html)
    feeds = []
    for node in tree.css('link[type="application/rss+xml"], link[type="application/atom+xml"]'):
        href = node.attributes.get("href")
        if href:
            feeds.append(href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/"))
    return feeds


# --- slug probe: custom career pages backed by an ATS ----------------------

ATS_MARKERS = {
    "greenhouse": re.compile(r"gh_jid|gh_src|greenhouse", re.I),
    "lever": re.compile(r"lever\.co|lever-", re.I),
    "ashby": re.compile(r"ashbyhq|ashby_jid", re.I),
}


def probe_ats_by_slug(url: str, html: str) -> Optional[tuple[str, str, list[JobPosting]]]:
    """Custom careers pages often front an ATS whose board token is just
    the company's domain slug (stripe.com -> greenhouse board 'stripe').
    Only probes when the page itself carries that ATS's markers, and only
    accepts the result when several API job titles literally appear in the
    page HTML — so a slug collision with another company can't return the
    wrong board.
    """
    slug = _domain_slug(url)
    if not slug or slug in ("www", "jobs", "careers"):
        return None
    # Markers make a platform the first candidate, but their absence
    # doesn't veto the probe: e.g. stripe.com's *static* HTML carries no
    # greenhouse strings at all, yet dozens of its greenhouse-API job
    # titles appear verbatim in it. The title cross-check is the gate.
    ordered = sorted(ATS_FETCHERS, key=lambda p: 0 if ATS_MARKERS[p].search(html) else 1)
    for platform in ordered:
        jobs = ATS_FETCHERS[platform](slug)
        if len(jobs) < 2:
            continue
        if _titles_confirm(jobs, html):
            return platform, slug, jobs
    return None
