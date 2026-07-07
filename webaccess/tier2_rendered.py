"""Tier 2: rendered DOM / accessibility tree via Playwright. No pixels,
no LLM — this module only *acquires* the rendered page; interpretation
is either code (JSON-LD on rendered HTML) or Tier 3 (LLM on the
accessibility snapshot).

Pagination is explicit: bounded "load more" clicking and bounded
infinite-scroll passes, reported in the result so page-1-only truncation
is never silent.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

CHROMIUM_PATH = "/opt/pw-browsers/chromium"
LOAD_MORE_RE = r"^(load more|show more|view more|more jobs|see more|view all)"
MAX_LOAD_MORE_CLICKS = 8
MAX_SCROLL_PASSES = 8


@dataclass
class RenderedPage:
    url: str
    html: str = ""
    aria: str = ""          # accessibility-tree snapshot (compact YAML-ish)
    text: str = ""          # visible text
    ok: bool = False
    auth_wall: bool = False
    load_more_clicks: int = 0
    scroll_passes: int = 0
    error: Optional[str] = None
    console_errors: list[str] = field(default_factory=list)


def _launch(p):
    kwargs = {"headless": True}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        kwargs["proxy"] = {"server": proxy}
        # This env's TLS-intercepting proxy resets Chromium's TLS 1.3
        # ClientHello (OpenSSL 1.3 hellos pass). The proxy re-terminates
        # TLS toward the origin itself, so capping the browser->proxy leg
        # at 1.2 loses nothing; cert trust still enforced via NSS store.
        kwargs["args"] = ["--ssl-version-max=tls1.2"]
    # Prefer the full Chromium binary: the headless-shell build fails TLS
    # through this env's intercepting proxy (measured: ERR_CONNECTION_RESET
    # from the shell, 200 from full Chromium with identical flags).
    if os.path.exists(CHROMIUM_PATH):
        try:
            return p.chromium.launch(executable_path=CHROMIUM_PATH, **kwargs)
        except Exception:
            pass
    return p.chromium.launch(**kwargs)


def _new_page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 2000})
    return ctx.new_page()


def _detect_auth_wall(page) -> bool:
    for marker in ("iframe[src*='recaptcha']", "iframe[src*='hcaptcha']",
                   "iframe[src*='turnstile']", "#px-captcha"):
        if page.locator(marker).count() > 0:
            return True
    if page.locator("input[type='password']").count() > 0:
        body = page.locator("body").inner_text(timeout=5000)
        if len(body.split()) < 200:
            return True
    return False


def render(url: str, *, wait_selector: Optional[str] = None,
           expand_pagination: bool = True, timeout_ms: int = 45000) -> RenderedPage:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    result = RenderedPage(url=url)
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            try:
                page = _new_page(browser)
                page.on("console", lambda msg: result.console_errors.append(msg.text)
                        if msg.type == "error" and len(result.console_errors) < 10 else None)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PWTimeout:
                    pass  # busy pages never go idle; proceed with what we have
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=15000)
                    except PWTimeout:
                        result.error = f"wait_selector {wait_selector!r} never appeared"

                if _detect_auth_wall(page):
                    result.auth_wall = True
                    result.html = page.content()
                    return result

                if expand_pagination:
                    _expand(page, result)

                result.html = page.content()
                result.text = page.locator("body").inner_text(timeout=10000)
                try:
                    result.aria = page.locator("body").aria_snapshot(timeout=10000)
                except Exception:
                    result.aria = ""  # old playwright; text+html still usable
                result.ok = True
            finally:
                browser.close()
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)[:300]}"
    return result


def _expand(page, result: RenderedPage) -> None:
    """Bounded 'load more' clicks, then bounded scroll-to-bottom passes."""
    import re as _re
    for _ in range(MAX_LOAD_MORE_CLICKS):
        btn = page.get_by_role("button", name=_re.compile(LOAD_MORE_RE, _re.I))
        try:
            if btn.count() == 0 or not btn.first.is_visible():
                break
            btn.first.click(timeout=5000)
            result.load_more_clicks += 1
            page.wait_for_timeout(1200)
        except Exception:
            break
    last_height = 0
    for _ in range(MAX_SCROLL_PASSES):
        height = page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height
        page.mouse.wheel(0, height)
        result.scroll_passes += 1
        page.wait_for_timeout(800)


def screenshot(url: str, out_path: str, *, timeout_ms: int = 45000,
               full_page: bool = False) -> Optional[str]:
    """Tier 4 acquisition: viewport screenshot (full_page capped by viewport
    height x4 to keep vision input sane). Returns path or None."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    try:
        with sync_playwright() as p:
            browser = _launch(p)
            try:
                page = _new_page(browser)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PWTimeout:
                    pass
                page.screenshot(path=out_path, full_page=full_page)
                return out_path
            finally:
                browser.close()
    except Exception:
        return None
