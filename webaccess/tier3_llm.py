"""Tier 3: LLM interprets already-acquired page content (static HTML text,
trafilatura markdown, or a Tier-2 accessibility snapshot). Never pixels.

Ladder B applies here: default model is haiku; the router escalates the
*model* to sonnet only when the haiku attempt fails schema validation —
independently of the extraction tier.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import ValidationError

from .llm import HAIKU, LLMResult, call_llm, extract_json
from .types import JobPosting

MAX_CONTENT_CHARS = 80_000


def _clip(content: str) -> str:
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    return content[:MAX_CONTENT_CHARS] + "\n...[truncated]"


def extract_jobs_llm(content: str, source_url: str, *,
                     model: str = HAIKU) -> tuple[Optional[list[JobPosting]], LLMResult]:
    prompt = f"""Extract every job posting from this page content (source: {source_url}).

Return ONLY a JSON array. Each element: {{"title": str, "location": str|null, "company": str|null, "url": str|null, "date_posted": "YYYY-MM-DD"|null, "salary": str|null, "department": str|null}}.
Rules: extract EVERY posting in the content — all of them, even if there are dozens; never stop early, never summarize or sample the list. Use null for anything not shown on the page — do NOT guess or infer. Resolve relative URLs against {source_url}. If there are no job postings, return [].
Before answering, count the postings in the content and make sure your array has that many elements.

PAGE CONTENT:
{_clip(content)}"""
    res = call_llm(prompt, model=model)
    if not res.ok:
        return None, res
    raw = extract_json(res.text)
    if not isinstance(raw, list):
        return None, res
    jobs = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            jobs.append(JobPosting(**{k: v for k, v in item.items()
                                      if k in JobPosting.model_fields}))
        except ValidationError:
            continue
    return jobs, res


def extract_fields_llm(content: str, source_url: str, fields: list[str],
                       question: Optional[str] = None, *,
                       model: str = HAIKU) -> tuple[Optional[dict[str, Any]], LLMResult]:
    field_list = ", ".join(f'"{f}"' for f in fields) if fields else '"answer"'
    q = f"\nQuestion to answer from the page: {question}" if question else ""
    prompt = f"""From this page content (source: {source_url}), extract the following fields: {field_list}.{q}

Return ONLY a JSON object with exactly those keys. Use null for anything not present on the page — do NOT guess from outside knowledge.

PAGE CONTENT:
{_clip(content)}"""
    res = call_llm(prompt, model=model)
    if not res.ok:
        return None, res
    raw = extract_json(res.text)
    if not isinstance(raw, dict):
        return None, res
    return raw, res


def vision_extract(image_path: str, source_url: str, task_description: str, *,
                   model: str = HAIKU) -> tuple[Optional[Any], LLMResult]:
    """Tier 4 interpretation: read a screenshot, same JSON contract."""
    prompt = f"""Read the screenshot at {image_path} (a rendering of {source_url}).

{task_description}

Return ONLY JSON. Use null for anything not visible — do NOT guess."""
    res = call_llm(prompt, model=model, allow_read_paths=True)
    if not res.ok:
        return None, res
    return extract_json(res.text), res
