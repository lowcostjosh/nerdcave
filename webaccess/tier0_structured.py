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

# Patterns that betray an embedded ATS inside a custom careers page.
ATS_EMBED_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.(?:eu\.)?greenhouse\.io/(?:embed/job_board\?(?:[^\"'\s]*&)?for=)?([A-Za-z0-9_-]+)")),
    ("greenhouse", re.compile(r"grnhse\.Iframe|grnh\.se")),
    ("lever", re.compile(r"(?:jobs|api)\.(?:eu\.)?lever\.co/(?:v0/postings/)?([A-Za-z0-9_-]+)")),
    ("ashby", re.compile(r"(?:jobs|api)\.ashbyhq\.com/(?:posting-api/job-board/)?([A-Za-z0-9_.-]+)")),
]


def detect_ats(url: str, html: Optional[str] = None) -> Optional[tuple[str, str]]:
    """Return (platform, board_token) if this URL or page is ATS-hosted."""
    for platform, pat in ATS_URL_PATTERNS:
        m = pat.search(url)
        if m:
            return platform, m.group(1)
    if html:
        for platform, pat in ATS_EMBED_PATTERNS:
            m = pat.search(html)
            if m and m.groups() and m.group(1):
                token = m.group(1)
                if token.lower() not in {"embed", "job_board", "v0", "postings"}:
                    return platform, token
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
