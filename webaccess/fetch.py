"""Polite HTTP layer: robots.txt respect, per-domain rate limiting,
retries with backoff, and an in-run URL cache."""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx

USER_AGENT = "webaccess-pipeline/0.1 (+respects robots.txt; contact: repo owner)"
DEFAULT_TIMEOUT = 20.0
MIN_INTERVAL_S = 1.0  # per-domain minimum spacing between requests
RETRIES = 3


@dataclass
class FetchResponse:
    url: str
    status_code: int
    text: str
    headers: dict
    ok: bool
    error: Optional[str] = None

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")


@dataclass
class PoliteFetcher:
    """Shared by all tiers so robots/rate-limit/cache apply uniformly."""
    timeout: float = DEFAULT_TIMEOUT
    _robots: dict[str, urllib.robotparser.RobotFileParser] = field(default_factory=dict)
    _last_hit: dict[str, float] = field(default_factory=dict)
    _cache: dict[str, FetchResponse] = field(default_factory=dict)

    def robots_allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
            try:
                resp = httpx.get(robots_url, timeout=10.0, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT})
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    # No robots.txt (or error page) -> everything allowed
                    rp.parse([])
            except Exception:
                rp.parse([])
            self._robots[host] = rp
        return rp.can_fetch(USER_AGENT, url) and rp.can_fetch("*", url)

    def _rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_hit.get(host, 0.0)
        wait = MIN_INTERVAL_S - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, *, use_cache: bool = True,
            respect_robots: bool = True) -> FetchResponse:
        if use_cache and url in self._cache:
            return self._cache[url]
        if respect_robots and not self.robots_allowed(url):
            return FetchResponse(url=url, status_code=0, text="", headers={},
                                 ok=False, error="blocked_robots")
        backoff = 2.0
        last_err = ""
        for attempt in range(RETRIES):
            self._rate_limit(url)
            try:
                resp = httpx.get(url, timeout=self.timeout, follow_redirects=True,
                                 headers={"User-Agent": USER_AGENT,
                                          "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8"})
                if resp.status_code >= 500 and attempt < RETRIES - 1:
                    last_err = f"HTTP {resp.status_code}"
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                out = FetchResponse(url=str(resp.url), status_code=resp.status_code,
                                    text=resp.text,
                                    headers={k.lower(): v for k, v in resp.headers.items()},
                                    ok=resp.status_code < 400)
                if use_cache:
                    self._cache[url] = out
                return out
            except httpx.HTTPError as e:
                last_err = f"{type(e).__name__}: {e}"
                if attempt < RETRIES - 1:
                    time.sleep(backoff)
                    backoff *= 2
        return FetchResponse(url=url, status_code=0, text="", headers={},
                             ok=False, error=f"unreachable: {last_err}")


# Module-level default so all tiers share one cache/rate-limiter per process.
FETCHER = PoliteFetcher()
