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

from .router import Router
from .types import Task


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

    task = Task(kind=args.kind,
                fields=[f.strip() for f in args.fields.split(",") if f.strip()],
                question=args.question)
    router = Router()
    if args.no_cache:
        router.cache.get = lambda *a, **k: None  # discovery-only run

    result = router.run(args.url, task, min_tier=args.min_tier)
    out = result.model_dump()
    if args.compact:
        out.pop("attempts", None)
    json.dump(out, sys.stdout, indent=2, default=str)
    print()
    return 0 if result.success or result.status in ("auth_required", "blocked_robots") else 1


if __name__ == "__main__":
    sys.exit(main())
