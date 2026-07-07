"""Site-profile cache: once a (domain, task-kind) resolves at some tier
with some recipe, save it so future runs skip discovery entirely.

Every cached recipe is re-validated on use (the router runs the same
success validator as discovery). A stale recipe fails LOUDLY: it is
marked stale with a reason, discovery re-runs, and the event is logged —
never silently returning wrong data.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "site_profiles.json")


@dataclass
class Recipe:
    tier: int                    # highest-cost capability used (0-4)
    method: str                  # e.g. "greenhouse_api", "jsonld", "trafilatura", "llm_on_aria"
    params: dict[str, Any] = field(default_factory=dict)  # e.g. {"platform": "greenhouse", "token": "stripe"}
    model: Optional[str] = None  # model that proved sufficient, if any
    created_at: float = field(default_factory=time.time)
    last_verified: float = field(default_factory=time.time)
    hits: int = 0
    stale: bool = False
    stale_reason: Optional[str] = None


class SiteProfileCache:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = os.path.abspath(path)
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.path)

    # Hosts where many tenants share one domain: the first path segment is
    # part of the site identity, or the recipe cache would hand one
    # company's recipe (and data!) to another.
    MULTI_TENANT_HOSTS = {
        "boards.greenhouse.io", "job-boards.greenhouse.io",
        "boards.eu.greenhouse.io", "job-boards.eu.greenhouse.io",
        "jobs.lever.co", "jobs.eu.lever.co",
        "jobs.ashbyhq.com", "apply.workable.com",
    }

    @classmethod
    def _key(cls, url: str, task_kind: str) -> tuple[str, str]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host in cls.MULTI_TENANT_HOSTS:
            seg = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
            host = f"{host}/{seg}"
        return host, task_kind

    def get(self, url: str, task_kind: str) -> Optional[Recipe]:
        domain, kind = self._key(url, task_kind)
        raw = (self._data.get(domain) or {}).get(kind)
        if not raw:
            return None
        recipe = Recipe(**raw)
        return None if recipe.stale else recipe

    def put(self, url: str, task_kind: str, recipe: Recipe) -> None:
        domain, kind = self._key(url, task_kind)
        self._data.setdefault(domain, {})[kind] = asdict(recipe)
        self._save()

    def confirm(self, url: str, task_kind: str) -> None:
        """Recipe re-validated successfully on this run."""
        domain, kind = self._key(url, task_kind)
        raw = (self._data.get(domain) or {}).get(kind)
        if raw:
            raw["last_verified"] = time.time()
            raw["hits"] = raw.get("hits", 0) + 1
            self._save()

    def invalidate(self, url: str, task_kind: str, reason: str) -> None:
        """Loud failure path: keep the record (for auditability) but mark
        it stale so discovery re-runs."""
        domain, kind = self._key(url, task_kind)
        raw = (self._data.get(domain) or {}).get(kind)
        if raw:
            raw["stale"] = True
            raw["stale_reason"] = reason
            self._save()
