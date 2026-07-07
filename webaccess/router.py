"""The tiered decision router.

Access-tier ladder (Ladder A): 0 structured -> 1 static HTML -> 2 rendered
DOM/a11y -> 4 vision. Tier 3 (LLM-planned interaction) is reserved for
tasks that need it; read-only extraction normally never does.

Model ladder (Ladder B), independent: code-only (no LLM) -> haiku ->
sonnet. Escalation on either ladder happens only on a MEASURED validation
failure, and every attempt is logged.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Optional

from . import tier0_structured as t0
from . import tier1_static as t1
from . import tier2_rendered as t2
from . import tier3_llm as t3
from .cache import Recipe, SiteProfileCache
from .fetch import FETCHER
from .llm import HAIKU, SONNET
from .types import Attempt, ExtractionResult, JobPosting, Task, Timer

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "run_log.jsonl")
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")


def _log(record: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(LOG_PATH)), exist_ok=True)
    record["ts"] = time.time()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


# --- success validators (what "measured failure" means) --------------------

def validate_jobs(data: Any) -> tuple[bool, str]:
    if not isinstance(data, list) or not data:
        return False, "no job postings extracted"
    titled = [j for j in data if isinstance(j, JobPosting) and j.title.strip()]
    if not titled:
        return False, "postings lack titles"
    with_detail = [j for j in titled if j.url or j.location]
    if not with_detail:
        return False, "no posting has a URL or location — likely a misparse"
    return True, ""


def validate_fields(data: Any, fields: list[str]) -> tuple[bool, str]:
    """ALL requested fields must be present — a null field is a measured
    failure that triggers escalation to the next tier. (If every tier
    leaves it null, the router returns the best partial result with an
    explicit note instead — see Router._discover.)"""
    if not isinstance(data, dict):
        return False, "not a dict"
    wanted = fields or ["answer"]
    empty = [f for f in wanted if data.get(f) in (None, "", [], {})]
    if empty:
        return False, f"fields still empty: {empty}"
    return True, ""


def validate_page_info(data: Any, has_question: bool = False) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    if not ((data.get("summary") or "").strip() or data.get("facts")):
        return False, "no summary or facts extracted"
    if has_question and data.get("answer") in (None, "", [], {}):
        return False, "question not answered from this tier's content"
    return True, ""


def _validator(task: Task) -> Callable[[Any], tuple[bool, str]]:
    if task.kind == "jobs":
        return validate_jobs
    if task.kind == "fields":
        return lambda d: validate_fields(d, task.fields)
    return lambda d: validate_page_info(d, has_question=bool(task.question))


def _partial_score(data: Any, task: Task) -> int:
    """How many requested keys a failed-validation dict still filled —
    used to keep the best partial result across tiers."""
    if not isinstance(data, dict):
        return 0
    if task.kind == "fields":
        wanted = task.fields or ["answer"]
    elif task.kind == "page_info":
        wanted = ["summary", "facts"] + (["answer"] if task.question else [])
    else:
        return 0
    return sum(1 for f in wanted if data.get(f) not in (None, "", [], {}))


class Router:
    def __init__(self, cache: Optional[SiteProfileCache] = None):
        self.cache = cache or SiteProfileCache()

    # -- public entry point --------------------------------------------
    def run(self, url: str, task: Task, *, min_tier: int = 0) -> ExtractionResult:
        """min_tier forces discovery to start at a given access tier —
        used by the validation harness to compare page extraction against
        Tier-0 API ground truth. Cached recipes below min_tier are skipped
        (not invalidated)."""
        result = ExtractionResult(url=url, task_kind=task.kind)
        validate = _validator(task)
        self._task = task
        self._best_partial: Optional[dict[str, Any]] = None

        recipe = self.cache.get(url, task.kind)
        if recipe is not None and min_tier and recipe.tier < min_tier and recipe.method != "auth_wall":
            recipe = None
        if recipe is not None:
            ok = self._try_recipe(url, task, recipe, result, validate)
            if ok:
                self.cache.confirm(url, task.kind)
                self._finish(result)
                return result
            # LOUD stale path: log, invalidate, fall through to discovery
            reason = f"cached recipe {recipe.method} failed revalidation: {result.notes}"
            self.cache.invalidate(url, task.kind, reason)
            _log({"event": "recipe_stale", "url": url, "task": task.kind,
                  "recipe": recipe.method, "reason": reason})
            result.notes = f"[cache invalidated: {reason}] "

        self._discover(url, task, result, validate, min_tier=min_tier)
        self._finish(result)
        return result

    def _finish(self, result: ExtractionResult) -> None:
        _log({"event": "run", "url": result.url, "task": result.task_kind,
              "success": result.success, "status": result.status,
              "tier": result.tier_used, "method": result.method,
              "model": result.model_used, "latency_s": round(result.latency_s, 2),
              "tokens": result.tokens_used,
              "attempts": [a.model_dump() for a in result.attempts]})

    # -- attempt bookkeeping --------------------------------------------
    def _attempt(self, result: ExtractionResult, tier: int, method: str,
                 fn: Callable[[], tuple[Any, Optional[str], int]],
                 validate: Callable[[Any], tuple[bool, str]],
                 model: Optional[str] = None) -> Optional[Any]:
        """Run one attempt; on validated success record it on the result and
        return the data, else log the failure and return None."""
        with Timer() as timer:
            try:
                data, err, tokens = fn()
            except Exception as e:
                data, err, tokens = None, f"{type(e).__name__}: {str(e)[:200]}", 0
        ok, why = (False, err) if err else validate(data)
        result.add_attempt(Attempt(tier=tier, method=method, model_used=model,
                                   latency_s=timer.elapsed, tokens_used=tokens or None,
                                   success=bool(ok), error=None if ok else (err or why)))
        if ok:
            result.data = self._serialize(data)
            result.tier_used = tier
            result.method = method
            result.model_used = model
            result.success = True
            result.status = "ok"
            return data
        result.notes = (result.notes + f" | {method}: {err or why}").strip(" |")
        # A failed-validation dict may still be the best partial answer we
        # ever get (e.g. a field that is genuinely absent at every tier).
        score = _partial_score(data, self._task)
        if score > (self._best_partial or {}).get("score", 0):
            self._best_partial = {"score": score, "data": data, "tier": tier,
                                  "method": method, "model": model,
                                  "reason": err or why}
        return None

    @staticmethod
    def _serialize(data: Any) -> Any:
        if isinstance(data, list):
            return [d.model_dump() if hasattr(d, "model_dump") else d for d in data]
        return data.model_dump() if hasattr(data, "model_dump") else data

    def _save_recipe(self, url: str, task: Task, tier: int, method: str,
                     params: dict[str, Any], model: Optional[str] = None) -> None:
        self.cache.put(url, task.kind, Recipe(tier=tier, method=method,
                                              params=params, model=model))

    # -- recipe replay ----------------------------------------------------
    def _try_recipe(self, url: str, task: Task, recipe: Recipe,
                    result: ExtractionResult,
                    validate: Callable[[Any], tuple[bool, str]]) -> bool:
        method, params = recipe.method, recipe.params
        if method == "auth_wall":
            # Recheck cheaply: still walled -> fail fast with a clear status.
            resp = t1.get_static(url)
            if resp.error == "blocked_robots" or (resp.text and t1.looks_like_auth_wall(resp)):
                result.status = "auth_required"
                result.success = False
                result.tier_used = 1
                result.method = "auth_wall_cached"
                result.notes = "cached: site requires authentication (recheck confirmed)"
                return True  # recipe still valid — the *site* is the blocker
            return False  # wall gone; rediscover

        if method == "ats_api":
            # Cross-check: if the URL itself names an ATS tenant, it must
            # match the cached token, or this recipe belongs to another site.
            detected = t0.detect_ats(url)
            if detected and detected != (params.get("platform"), params.get("token")):
                result.notes = (f"cached ATS token {params.get('token')!r} does not match "
                                f"URL tenant {detected[1]!r}")
                return False

        runner = {
            "ats_api": lambda: self._run_ats(params),
            "jsonld_static": lambda: self._run_jsonld_static(url),
            "static_trafilatura": lambda: self._run_static_trafilatura(url, task),
            "static_llm": lambda: self._run_static_llm(url, task, params.get("model") or recipe.model or HAIKU),
            "rendered_llm": lambda: self._run_rendered_llm(url, task, params.get("model") or recipe.model or HAIKU,
                                                           params.get("wait_selector")),
            "jsonld_rendered": lambda: self._run_jsonld_rendered(url, params.get("wait_selector")),
            "vision": lambda: self._run_vision(url, task, params.get("model") or recipe.model or HAIKU),
        }.get(method)
        if runner is None:
            return False
        data = self._attempt(result, recipe.tier, method + "(cached)", runner,
                             validate, model=recipe.model)
        return data is not None

    # -- discovery ladder --------------------------------------------------
    def _discover(self, url: str, task: Task, result: ExtractionResult,
                  validate: Callable[[Any], tuple[bool, str]],
                  min_tier: int = 0) -> None:
        # ---- Tier 0: ATS detected from the URL itself
        if task.kind == "jobs" and min_tier <= 0:
            ats = t0.detect_ats(url)
            if ats and self._attempt(result, 0, f"ats_api:{ats[0]}",
                                     lambda: self._run_ats({"platform": ats[0], "token": ats[1]}),
                                     validate) is not None:
                self._save_recipe(url, task, 0, "ats_api",
                                  {"platform": ats[0], "token": ats[1]})
                return

        # ---- Tier 1: static fetch (shared input for several branches)
        resp = t1.get_static(url) if min_tier <= 1 else t1.FetchResponse(
            url=url, status_code=0, text="", headers={}, ok=False,
            error="skipped: min_tier > 1")
        if resp.error == "blocked_robots":
            result.status = "blocked_robots"
            result.notes = "robots.txt disallows fetching this URL; not proceeding"
            return
        static_ok = resp.ok and bool(resp.text)
        if static_ok and t1.looks_like_auth_wall(resp):
            result.status = "auth_required"
            result.notes = ("login wall / paywall / CAPTCHA detected — out of scope, "
                            "needs authenticated access; not attempting to bypass")
            self.cache.put(url, task.kind, Recipe(tier=1, method="auth_wall", params={}))
            return

        if static_ok:
            html = resp.text
            js_shell = t1.looks_like_js_shell(html)

            # Tier 0 via page contents: embedded ATS, JSON-LD
            if task.kind == "jobs" and min_tier <= 0:
                ats = t0.detect_ats(url, html)
                if ats and self._attempt(result, 0, f"ats_api_embed:{ats[0]}",
                                         lambda: self._run_ats({"platform": ats[0], "token": ats[1]}),
                                         validate) is not None:
                    self._save_recipe(url, task, 0, "ats_api",
                                      {"platform": ats[0], "token": ats[1]})
                    return
                if self._attempt(result, 0, "jsonld_static",
                                 lambda: self._run_jsonld_static(url),
                                 validate) is not None:
                    self._save_recipe(url, task, 0, "jsonld_static", {})
                    return
            elif task.kind != "jobs":
                # page_info / fields: code-only static extraction first
                if self._attempt(result, 1, "static_trafilatura",
                                 lambda: self._run_static_trafilatura(url, task),
                                 validate) is not None:
                    self._save_recipe(url, task, 1, "static_trafilatura", {})
                    return

            # Tier 1 + LLM (haiku -> sonnet) on static content, unless shell
            if not js_shell:
                for model in (HAIKU, SONNET):
                    if self._attempt(result, 1, "static_llm",
                                     lambda m=model: self._run_static_llm(url, task, m),
                                     validate, model=model) is not None:
                        self._save_recipe(url, task, 1, "static_llm", {"model": model}, model)
                        return

        # ---- Tier 2: rendered DOM / accessibility tree
        if min_tier > 2:
            page = t2.RenderedPage(url=url, error="skipped: min_tier > 2")
        else:
            page = t2.render(url)
        if page.auth_wall:
            result.status = "auth_required"
            result.notes = "auth wall detected after rendering — out of scope, needs auth"
            self.cache.put(url, task.kind, Recipe(tier=2, method="auth_wall", params={}))
            return
        if page.ok:
            if task.kind == "jobs" and min_tier <= 0:
                ats = t0.detect_ats(url, page.html)
                if ats and self._attempt(result, 0, f"ats_api_rendered:{ats[0]}",
                                         lambda: self._run_ats({"platform": ats[0], "token": ats[1]}),
                                         validate) is not None:
                    self._save_recipe(url, task, 0, "ats_api",
                                      {"platform": ats[0], "token": ats[1]})
                    return
            if task.kind == "jobs":
                if self._attempt(result, 2, "jsonld_rendered",
                                 lambda: self._jsonld_from(page),
                                 validate) is not None:
                    self._save_recipe(url, task, 2, "jsonld_rendered", {})
                    return
            for model in (HAIKU, SONNET):
                if self._attempt(result, 2, "rendered_llm",
                                 lambda m=model: self._llm_from_rendered(page, url, task, m),
                                 validate, model=model) is not None:
                    self._save_recipe(url, task, 2, "rendered_llm", {"model": model}, model)
                    return

        # ---- Tier 4: vision, the last resort
        for model in (HAIKU, SONNET):
            if self._attempt(result, 4, "vision",
                             lambda m=model: self._run_vision(url, task, m),
                             validate, model=model) is not None:
                self._save_recipe(url, task, 4, "vision", {"model": model}, model)
                return

        # Every tier exhausted. If a tier produced a partial dict, return it
        # honestly rather than nothing — flagged, and never cached as a recipe.
        if self._best_partial is not None:
            bp = self._best_partial
            result.data = self._serialize(bp["data"])
            result.tier_used = bp["tier"]
            result.method = bp["method"]
            result.model_used = bp["model"]
            result.success = True
            result.status = "ok"
            result.notes = (f"PARTIAL after exhausting tiers: {bp['reason']} "
                            f"(best attempt: {bp['method']}) | " + result.notes).strip(" |")
            return

        result.success = False
        if result.status == "error":
            reachable = static_ok or page.ok
            result.status = "no_data" if reachable else "unreachable"

    # -- tier runners: each returns (data, error, tokens) -------------------
    def _run_ats(self, params: dict[str, Any]) -> tuple[Any, Optional[str], int]:
        fetcher = t0.ATS_FETCHERS.get(params.get("platform", ""))
        if fetcher is None:
            return None, f"unknown ATS platform {params.get('platform')}", 0
        return fetcher(params["token"]), None, 0

    def _run_jsonld_static(self, url: str) -> tuple[Any, Optional[str], int]:
        resp = t1.get_static(url)
        if not resp.ok:
            return None, resp.error or f"HTTP {resp.status_code}", 0
        return t0.extract_jsonld_jobs(resp.text), None, 0

    def _run_jsonld_rendered(self, url: str, wait_selector: Optional[str]) -> tuple[Any, Optional[str], int]:
        page = t2.render(url, wait_selector=wait_selector)
        if not page.ok:
            return None, page.error or "render failed", 0
        return self._jsonld_from(page)

    def _jsonld_from(self, page: t2.RenderedPage) -> tuple[Any, Optional[str], int]:
        return t0.extract_jsonld_jobs(page.html), None, 0

    def _run_static_trafilatura(self, url: str, task: Task) -> tuple[Any, Optional[str], int]:
        resp = t1.get_static(url)
        if not resp.ok:
            return None, resp.error or f"HTTP {resp.status_code}", 0
        if task.kind != "page_info" or task.fields or task.question:
            return None, "trafilatura path only serves plain page_info", 0
        if t1.looks_like_js_shell(resp.text):
            return None, "static HTML is a JS shell", 0
        content = t1.extract_main_content(resp.text, url)
        if not content or len(content.split()) < 40:
            return None, "no substantive main content", 0
        import trafilatura
        meta = trafilatura.extract_metadata(resp.text)
        facts = t0.extract_jsonld_facts(resp.text)
        return {"title": (meta.title if meta else None),
                "summary": content[:1500],
                "facts": facts}, None, 0

    MAX_STATIC_PAGES = 5

    def _content_for_llm(self, url: str, *, paginate: bool = False) -> tuple[Optional[str], Optional[str]]:
        """Static content for LLM interpretation. With paginate=True,
        follows rel-next style links (bounded) so list pages don't silently
        truncate to page 1."""
        parts: list[str] = []
        current: Optional[str] = url
        seen: set[str] = set()
        for page_no in range(self.MAX_STATIC_PAGES if paginate else 1):
            if not current or current in seen:
                break
            seen.add(current)
            resp = t1.get_static(current)
            if not resp.ok:
                if page_no == 0:
                    return None, resp.error or f"HTTP {resp.status_code}"
                break
            md = t1.extract_main_content(resp.text, current)
            text = md if md and len(md) > 400 else t1.visible_text(resp.text)
            parts.append(f"[page {page_no + 1}: {current}]\n{text}")
            current = t1.find_next_page(resp.text, current) if paginate else None
        if not parts:
            return None, "no content"
        if current and len(seen) >= self.MAX_STATIC_PAGES:
            parts.append(f"[NOTE: more pages exist beyond {self.MAX_STATIC_PAGES}; results may be partial]")
        return "\n\n".join(parts), None

    def _run_static_llm(self, url: str, task: Task, model: str) -> tuple[Any, Optional[str], int]:
        content, err = self._content_for_llm(url, paginate=(task.kind == "jobs"))
        if err:
            return None, err, 0
        return self._llm_interpret(content, url, task, model)

    def _run_rendered_llm(self, url: str, task: Task, model: str,
                          wait_selector: Optional[str]) -> tuple[Any, Optional[str], int]:
        page = t2.render(url, wait_selector=wait_selector)
        if not page.ok:
            return None, page.error or "render failed", 0
        return self._llm_from_rendered(page, url, task, model)

    def _llm_from_rendered(self, page: t2.RenderedPage, url: str, task: Task,
                           model: str) -> tuple[Any, Optional[str], int]:
        # Prefer the accessibility snapshot: it is compact AND carries
        # semantics plain text lacks (roles, placeholders, labels). On
        # small screens, send both — cheap, and each covers the other's
        # blind spots.
        content = page.aria or page.text
        if page.aria and page.text and len(page.aria.split()) < 200:
            content = page.aria + "\n\n[VISIBLE TEXT]\n" + page.text
        if page.load_more_clicks or page.scroll_passes:
            content = (f"[pagination expanded: {page.load_more_clicks} load-more clicks, "
                       f"{page.scroll_passes} scroll passes]\n" + content)
        return self._llm_interpret(content, url, task, model)

    def _llm_interpret(self, content: Optional[str], url: str, task: Task,
                       model: str) -> tuple[Any, Optional[str], int]:
        if not content or len(content.split()) < 10:
            return None, "no content to interpret", 0
        if task.kind == "jobs":
            jobs, res = t3.extract_jobs_llm(content, url, model=model)
            return jobs, res.error, res.tokens_used
        if task.kind == "fields":
            data, res = t3.extract_fields_llm(content, url, task.fields,
                                              task.question, model=model)
            return data, res.error, res.tokens_used
        keys = ["title", "summary", "facts"] + (["answer"] if task.question else [])
        data, res = t3.extract_fields_llm(
            content, url, keys,
            task.question or "Summarize what this page is and its key facts.",
            model=model)
        return data, res.error, res.tokens_used

    def _run_vision(self, url: str, task: Task, model: str) -> tuple[Any, Optional[str], int]:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        from urllib.parse import urlparse
        safe = urlparse(url).netloc.replace(":", "_")
        path = os.path.join(SCREENSHOT_DIR, f"{safe}_{int(time.time())}.png")
        shot = t2.screenshot(url, path)
        if shot is None:
            return None, "screenshot failed", 0
        if task.kind == "jobs":
            desc = ('Extract every visible job posting as a JSON array of '
                    '{"title", "location", "company", "url", "date_posted", "salary", "department"} '
                    '(null when not visible).')
        elif task.kind == "fields":
            desc = (f"Extract these fields as a JSON object: {task.fields}. "
                    f"{task.question or ''} Use null when not visible.")
        else:
            desc = ('Return a JSON object {"title", "summary", "facts"} describing this page. '
                    + (task.question or ""))
        raw, res = t3.vision_extract(path, url, desc, model=model)
        if task.kind == "jobs" and isinstance(raw, list):
            from pydantic import ValidationError
            jobs = []
            for item in raw:
                if isinstance(item, dict):
                    try:
                        jobs.append(JobPosting(**{k: v for k, v in item.items()
                                                  if k in JobPosting.model_fields}))
                    except ValidationError:
                        continue
            return jobs, res.error, res.tokens_used
        return raw, res.error, res.tokens_used
