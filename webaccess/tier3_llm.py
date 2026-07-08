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
# Above this, a jobs page is split into paragraph-boundary chunks so a huge
# board isn't silently truncated at MAX_CONTENT_CHARS (and no single call
# has to hold the whole thing).
CHUNK_THRESHOLD = 60_000
MAX_CHUNKS = 3


def _clip(content: str) -> str:
    if len(content) <= MAX_CONTENT_CHARS:
        return content
    return content[:MAX_CONTENT_CHARS] + "\n...[truncated]"


def _split_on_paragraphs(content: str, max_chunks: int, threshold: int) -> list[str]:
    """Greedily pack paragraphs into at most max_chunks chunks, each roughly
    the same size and comfortably under MAX_CONTENT_CHARS."""
    target = max(threshold, len(content) // max_chunks + 1)
    chunks: list[str] = []
    cur = ""
    for para in content.split("\n\n"):
        if cur and len(cur) + len(para) > target and len(chunks) < max_chunks - 1:
            chunks.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        chunks.append(cur)
    return chunks


def _jobs_prompt(content: str, source_url: str) -> str:
    return f"""Extract every job posting from this page content (source: {source_url}).

Return ONLY a JSON array. Each element: {{"title": str, "location": str|null, "company": str|null, "url": str|null, "date_posted": "YYYY-MM-DD"|null, "salary": str|null, "department": str|null}}.
Rules: extract EVERY posting in the content — all of them, even if there are dozens; never stop early, never summarize or sample the list. Use null for anything not shown on the page — do NOT guess or infer. Resolve relative URLs against {source_url}. If there are no job postings, return [].
Before answering, count the postings in the content and make sure your array has that many elements.

PAGE CONTENT:
{_clip(content)}"""


def _parse_jobs(text: str) -> Optional[list[JobPosting]]:
    raw = extract_json(text)
    if not isinstance(raw, list):
        return None
    jobs = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            jobs.append(JobPosting(**{k: v for k, v in item.items()
                                      if k in JobPosting.model_fields}))
        except ValidationError:
            continue
    return jobs


def _dedupe_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    seen: set[tuple[str, str]] = set()
    out = []
    for j in jobs:
        key = (j.title.strip().lower(), (j.location or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


def extract_jobs_llm(content: str, source_url: str, *,
                     model: str = HAIKU) -> tuple[Optional[list[JobPosting]], LLMResult]:
    if len(content) <= CHUNK_THRESHOLD:
        res = call_llm(_jobs_prompt(content, source_url), model=model)
        if not res.ok:
            return None, res
        return _parse_jobs(res.text), res

    # Large board: extract per chunk, merge, dedupe by (title, location).
    chunks = _split_on_paragraphs(content, MAX_CHUNKS, CHUNK_THRESHOLD)
    merged: list[JobPosting] = []
    total_tokens = 0
    last_err: Optional[str] = None
    for chunk in chunks:
        res = call_llm(_jobs_prompt(chunk, source_url), model=model)
        total_tokens += res.tokens_used
        if not res.ok:
            last_err = res.error
            continue
        jobs = _parse_jobs(res.text)
        if jobs:
            merged.extend(jobs)
    deduped = _dedupe_jobs(merged)
    note = f"chunked: {len(chunks)} passes -> {len(deduped)} unique jobs"
    out = LLMResult(text="", model=model, tokens_used=total_tokens,
                    ok=bool(deduped),
                    error=None if deduped else (last_err or "no jobs across chunks"),
                    note=note)
    return (deduped or None), out


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
