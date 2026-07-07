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

AUTH_WALL_RE = re.compile(
    r"(sign in to continue|log ?in to (?:view|continue|see)|create an account to"
    r"|session expired|authentication required|checking your browser|verify you are"
    r" ?(?:a )?human|captcha|cf-challenge|access denied)", re.I)
CAPTCHA_MARKERS = ("recaptcha", "hcaptcha", "cf-turnstile", "captcha-delivery",
                   "px-captcha", "datadome")


def get_static(url: str) -> FetchResponse:
    return FETCHER.get(url)


def looks_like_auth_wall(resp: FetchResponse) -> bool:
    if resp.status_code in (401, 403, 407):
        return True
    head = resp.text[:20000].lower()
    if any(m in head for m in CAPTCHA_MARKERS):
        return True
    # login-only pages: a password field and almost no other content
    tree = HTMLParser(resp.text)
    if tree.css_first('input[type="password"]') is not None:
        body_text = (tree.body.text(separator=" ") if tree.body else "")
        if len(body_text.split()) < 200:
            return True
    return bool(AUTH_WALL_RE.search(head)) and resp.status_code != 200 or False


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
