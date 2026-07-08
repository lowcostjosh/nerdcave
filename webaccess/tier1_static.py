"""Tier 1: static HTML over plain HTTP — no JS execution, no LLM.

Code-only interpretation: trafilatura for main content, selectolax for
structure, plus heuristics that decide whether escalation is needed
(JS shell detection, auth-wall detection).
"""
from __future__ import annotations

import re
from typing import Optional

import trafilatura
from selectolax.parser import HTMLParser

from .fetch import FETCHER, FetchResponse

# Login / paywall phrasing. Rich content pages routinely carry "sign in"
# in a nav or footer, so these only signal a wall on a non-200 response.
AUTH_WALL_RE = re.compile(
    r"(sign in to continue|log ?in to (?:view|continue|see)|create an account to"
    r"|session expired|authentication required|access denied)", re.I)
# Bot-challenge / interstitial phrasing. A challenge page IS a wall
# regardless of status code (Cloudflare serves these as 200/403/503).
CHALLENGE_RE = re.compile(
    r"(checking your browser|just a moment\.?\.?\.?|verify you are ?(?:a )?human"
    r"|attention required|cf-chl|__cf_chl|px-captcha|datadome)", re.I)
CAPTCHA_MARKERS = ("recaptcha", "hcaptcha", "cf-turnstile", "captcha-delivery",
                   "px-captcha", "datadome")
# A page with fewer visible words than this is "sparse" — a plausible
# challenge/login interstitial rather than real content.
SPARSE_WORDS = 200


def get_static(url: str) -> FetchResponse:
    return FETCHER.get(url)


def looks_like_auth_wall(resp: FetchResponse) -> bool:
    """True only for genuine walls. A captcha *widget* embedded in a form on
    an otherwise rich content page is NOT a wall — only sparse challenge
    interstitials and login-only pages are."""
    if resp.status_code in (401, 403, 407):
        return True
    text = resp.text or ""
    head = text[:20000].lower()
    # An explicit bot-challenge interstitial is always a wall.
    if CHALLENGE_RE.search(head):
        return True
    sparse = len(visible_text(text).split()) < SPARSE_WORDS
    # A captcha widget only signals a wall on a sparse page; a content-rich
    # page that merely embeds reCAPTCHA in a contact/login form passes.
    if sparse and any(m in head for m in CAPTCHA_MARKERS):
        return True
    # Login-only page: a password field with almost no other content.
    tree = HTMLParser(text)
    if sparse and tree.css_first('input[type="password"]') is not None:
        return True
    # Generic login/paywall phrasing counts only on a non-200 response.
    if resp.status_code != 200 and AUTH_WALL_RE.search(head):
        return True
    return False


def visible_text(html: str) -> str:
    tree = HTMLParser(html)
    for sel in ("script", "style", "noscript", "svg", "template"):
        for node in tree.css(sel):
            node.decompose()
    return tree.body.text(separator="\n") if tree.body else ""


def looks_like_js_shell(html: str) -> bool:
    """True when the static HTML is an empty SPA shell that needs Tier 2."""
    text = visible_text(html)
    words = len(text.split())
    if words < 60:
        return True
    low = html.lower()
    if ("enable javascript" in low or "requires javascript" in low) and words < 200:
        return True
    return False


def extract_main_content(html: str, url: str) -> Optional[str]:
    """trafilatura main-content extraction -> markdown-ish text. No LLM."""
    return trafilatura.extract(html, url=url, include_links=True,
                               include_tables=True, output_format="markdown")


def find_next_page(html: str, current_url: str) -> Optional[str]:
    """Explicit pagination discovery: rel=next or a 'next' link."""
    tree = HTMLParser(html)
    node = tree.css_first('link[rel="next"], a[rel="next"]')
    if node is None:
        for a in tree.css("a"):
            label = (a.text() or "").strip().lower()
            if label in ("next", "next page", "older posts", "›", "»", "more jobs"):
                node = a
                break
    if node is None:
        return None
    href = node.attributes.get("href")
    if not href or href.startswith("#"):
        return None
    if href.startswith("http"):
        return href
    from urllib.parse import urljoin
    return urljoin(current_url, href)
