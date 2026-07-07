"""Core result and task types for the tiered web-access pipeline."""
from __future__ import annotations

import time
from enum import IntEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Tier(IntEnum):
    STRUCTURED = 0   # official APIs, JSON-LD, sitemap, RSS, llms.txt
    STATIC_HTML = 1  # plain HTTP GET, no JS
    RENDERED_DOM = 2  # Playwright accessibility tree / rendered DOM, no pixels
    LLM_DOM = 3      # LLM interprets cleaned DOM/markdown
    VISION = 4       # screenshots — last resort


Status = Literal[
    "ok",
    "auth_required",   # login wall / paywall / CAPTCHA — out of scope, never defeated
    "blocked_robots",  # robots.txt disallows; we respect it
    "unreachable",     # network / DNS / 5xx after retries
    "no_data",         # reachable but the requested data is not on this page
    "error",           # pipeline bug or unhandled failure
]


class Attempt(BaseModel):
    """One tier attempt, logged whether it succeeded or not."""
    tier: int
    method: str
    model_used: Optional[str] = None
    latency_s: float = 0.0
    tokens_used: Optional[int] = None
    success: bool = False
    error: Optional[str] = None


class ExtractionResult(BaseModel):
    url: str
    task_kind: str
    data: Any = None
    tier_used: Optional[int] = None
    method: Optional[str] = None
    model_used: Optional[str] = None
    latency_s: float = 0.0
    tokens_used: int = 0
    success: bool = False
    status: Status = "error"
    notes: str = ""
    attempts: list[Attempt] = Field(default_factory=list)

    def add_attempt(self, attempt: Attempt) -> None:
        self.attempts.append(attempt)
        self.latency_s += attempt.latency_s
        if attempt.tokens_used:
            self.tokens_used += attempt.tokens_used


class JobPosting(BaseModel):
    """Schema for job extraction tasks; validation gate for every tier."""
    title: str
    location: Optional[str] = None
    company: Optional[str] = None
    url: Optional[str] = None
    date_posted: Optional[str] = None
    salary: Optional[str] = None
    department: Optional[str] = None


class PageInfo(BaseModel):
    """Schema for general page-information tasks."""
    title: Optional[str] = None
    summary: Optional[str] = None
    facts: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """What to get from a URL.

    kind:
      jobs      -> data is list[JobPosting]
      fields    -> data is dict matching `fields` keys
      page_info -> data is PageInfo
    """
    kind: Literal["jobs", "fields", "page_info"] = "page_info"
    fields: list[str] = Field(default_factory=list)
    question: Optional[str] = None


class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.monotonic()
        self.elapsed = 0.0
        return self

    def __exit__(self, *exc: Any) -> None:
        self.elapsed = time.monotonic() - self.start
