"""CLI entry point — the common harness interface from Phase 2, and what
the packaged Skill invokes.

    python -m webaccess.cli --url URL --kind jobs
    python -m webaccess.cli --url URL --kind fields --fields price,contact_email
    python -m webaccess.cli --url URL --kind page_info --question "What does this company sell?"

Prints one JSON object: {data, tier_used, method, model_used, latency_s,
tokens_used, success, status, notes, attempts}.
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse

from .router import Router
from .types import ExtractionResult, Task


def _emit(result: ExtractionResult, compact: bool) -> None:
    out = result.model_dump()
    if compact:
        out.pop("attempts", None)
    json.dump(out, sys.stdout, indent=2, default=str)
    print()


def _error_result(url: str, kind: str, notes: str) -> ExtractionResult:
    r = ExtractionResult(url=url, task_kind=kind)
    r.status = "error"
    r.success = False
    r.notes = notes
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tiered web extraction")
    ap.add_argument("--url", required=True)
    ap.add_argument("--kind", choices=["jobs", "fields", "page_info"],
                    default="page_info")
    ap.add_argument("--fields", default="", help="comma-separated field names")
    ap.add_argument("--question", default=None)
    ap.add_argument("--no-cache", action="store_true",
                    help="ignore the site-profile cache for this run")
    ap.add_argument("--min-tier", type=int, default=0,
                    help="force discovery to start at this access tier "
                         "(validation/testing only)")
    ap.add_argument("--compact", action="store_true", help="omit attempt log")
    args = ap.parse_args(argv)

    # Malformed input is a caller error, not a network outcome: emit a
    # valid error-shaped result and exit 2 rather than crashing downstream.
    parsed = urlparse(args.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        _emit(_error_result(args.url, args.kind,
                            f"invalid URL: expected http(s)://host, got {args.url!r}"),
              args.compact)
        return 2

    task = Task(kind=args.kind,
                fields=[f.strip() for f in args.fields.split(",") if f.strip()],
                question=args.question)
    router = Router()
    if args.no_cache:
        router.cache.get = lambda *a, **k: None  # discovery-only run

    try:
        result = router.run(args.url, task, min_tier=args.min_tier)
    except Exception as e:  # never dump a traceback to stdout / emit no JSON
        _emit(_error_result(args.url, args.kind, f"{type(e).__name__}: {e}"),
              args.compact)
        return 2

    _emit(result, args.compact)
    return 0 if result.success or result.status in ("auth_required", "blocked_robots") else 1


if __name__ == "__main__":
    sys.exit(main())
