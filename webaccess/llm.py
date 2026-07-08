"""LLM gateway via the `claude` CLI in headless mode.

Rationale: this pipeline ships as a Claude Code Skill, so the host
environment always has `claude` available and authenticated. No raw API
key handling, and Ladder B (cheapest capable model) is a parameter:
default `haiku` for routine interpretation, escalate only on validation
failure.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Optional

HAIKU = "haiku"
SONNET = "sonnet"
# A single 275-posting board measured at 157s; raised from 180 so bigger
# boards (and chunked passes) don't clip mid-extraction.
DEFAULT_TIMEOUT_S = 240


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_used: int  # input + output as reported by the CLI
    ok: bool
    error: Optional[str] = None
    note: Optional[str] = None  # non-error commentary (e.g. chunk counts)


def call_llm(prompt: str, *, model: str = HAIKU, allow_read_paths: bool = False,
             timeout_s: int = DEFAULT_TIMEOUT_S) -> LLMResult:
    """One-shot headless call. Set allow_read_paths=True for vision tasks
    where the prompt references a local screenshot the model must Read."""
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--max-turns", "3" if allow_read_paths else "1",
    ]
    if allow_read_paths:
        cmd += ["--allowedTools", "Read"]
    else:
        cmd += ["--allowedTools", ""]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return LLMResult(text="", model=model, tokens_used=0, ok=False,
                         error=f"llm timeout after {timeout_s}s")
    if proc.returncode != 0:
        return LLMResult(text="", model=model, tokens_used=0, ok=False,
                         error=f"claude CLI exit {proc.returncode}: {proc.stderr[:500]}")
    try:
        payload = json.loads(proc.stdout)
        usage = payload.get("usage", {})
        # cache_creation counts: the CLI re-uploads its system prompt per call
        tokens = (int(usage.get("input_tokens", 0))
                  + int(usage.get("cache_creation_input_tokens", 0))
                  + int(usage.get("cache_read_input_tokens", 0))
                  + int(usage.get("output_tokens", 0)))
        return LLMResult(text=payload.get("result", ""), model=model,
                         tokens_used=tokens, ok=not payload.get("is_error", False))
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return LLMResult(text=proc.stdout, model=model, tokens_used=0, ok=False,
                         error=f"unparseable CLI output: {e}")


def extract_json(text: str) -> Optional[object]:
    """Pull the first JSON object/array out of an LLM reply that may wrap
    it in prose or a code fence."""
    text = text.strip()
    # Try the outermost container first: whichever bracket appears earliest.
    candidates = sorted(
        (pair for pair in (("[", "]"), ("{", "}")) if text.find(pair[0]) != -1),
        key=lambda pair: text.find(pair[0]))
    for start_char, end_char in candidates:
        start = text.find(start_char)
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\" and in_str:
                escape = True
            elif c == '"':
                in_str = not in_str
            elif not in_str:
                if c == start_char:
                    depth += 1
                elif c == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
        # fall through to try the other bracket type
    return None
