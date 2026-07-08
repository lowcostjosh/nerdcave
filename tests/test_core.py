"""Offline unit tests — no network, no LLM, no browser."""
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from webaccess.cache import Recipe, SiteProfileCache
from webaccess.fetch import FetchResponse
from webaccess.llm import extract_json
from webaccess.router import validate_fields, validate_jobs, validate_page_info
from webaccess.tier0_structured import detect_ats, extract_jsonld_jobs
from webaccess.tier1_static import looks_like_auth_wall, looks_like_js_shell
from webaccess.types import JobPosting


def _resp(text, status=200):
    return FetchResponse(url="https://x.example.com", status_code=status,
                         text=text, headers={}, ok=status < 400)


_RICH = " ".join(f"content{i}" for i in range(400))


# --- ATS detection ---------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://boards.greenhouse.io/stripe", ("greenhouse", "stripe")),
    ("https://job-boards.greenhouse.io/gitlab", ("greenhouse", "gitlab")),
    ("https://job-boards.eu.greenhouse.io/acme", ("greenhouse", "acme")),
    ("https://jobs.lever.co/palantir", ("lever", "palantir")),
    ("https://jobs.ashbyhq.com/openai", ("ashby", "openai")),
    ("https://example.com/careers", None),
])
def test_detect_ats_url(url, expected):
    assert detect_ats(url) == expected


def test_detect_ats_embed():
    html = '<iframe src="https://boards.greenhouse.io/embed/job_board?for=acmecorp"></iframe>'
    assert detect_ats("https://acme.example.com/careers", html) == ("greenhouse", "acmecorp")


def test_detect_ats_embed_ignores_reserved_words():
    assert detect_ats("https://x.example.com", "see boards.greenhouse.io/embed") is None


# --- P0-2: ATS embed-token crosstalk ---------------------------------------

def test_detect_ats_blog_link_does_not_crosstalk():
    # A blog on someblog.com merely LINKS Palantir's lever board once.
    # Weak evidence: token != domain slug, single occurrence -> must NOT
    # return palantir (would otherwise serve Palantir's jobs as this site's).
    html = '<article>Cool company: <a href="https://jobs.lever.co/palantir">careers</a></article>'
    assert detect_ats("https://someblog.example.com/post", html) is None


def test_detect_ats_strong_embed_still_detected():
    # A real Lever apply/postings embed carries the API endpoint -> strong.
    html = '<script>fetch("https://api.lever.co/v0/postings/realco?mode=json")</script>'
    assert detect_ats("https://realco.example.com/careers", html) == ("lever", "realco")
    gh = '<div id="grnhse_app"></div><script>Grnhse.Iframe.load({ for: "widgetco" });</script>'
    assert detect_ats("https://widgetco.example.com/jobs", gh) == ("greenhouse", "widgetco")


def test_detect_ats_slug_match_link_accepted():
    # stripe.com linking boards.greenhouse.io/stripe: token == domain slug,
    # so it is self-referential and trustworthy (no network needed).
    html = '<a href="https://boards.greenhouse.io/stripe">Open roles</a>'
    assert detect_ats("https://stripe.com/jobs", html) == ("greenhouse", "stripe")


# --- P0-1: CAPTCHA false positive ------------------------------------------

def test_auth_wall_rich_page_with_recaptcha_is_not_a_wall():
    html = f'<html><body><p>{_RICH}</p>' \
           '<script src="https://www.google.com/recaptcha/api.js"></script></body></html>'
    assert looks_like_auth_wall(_resp(html, status=200)) is False


def test_auth_wall_sparse_cloudflare_challenge_is_a_wall():
    html = '<html><body><h1>Just a moment...</h1>' \
           '<p>Checking your browser before accessing the site.</p></body></html>'
    assert looks_like_auth_wall(_resp(html, status=200)) is True


def test_auth_wall_403_is_a_wall():
    assert looks_like_auth_wall(_resp("<html><body>nope</body></html>", status=403)) is True


def test_auth_wall_password_form_sparse_is_a_wall():
    html = '<html><body><form><input type="password"></form>Sign in</body></html>'
    assert looks_like_auth_wall(_resp(html, status=200)) is True


def test_auth_wall_password_form_on_rich_page_is_not_a_wall():
    # A newsletter/login box in the footer of a long article must pass.
    html = f'<html><body><article>{_RICH}</article>' \
           '<footer><form><input type="password">Sign in</form></footer></body></html>'
    assert looks_like_auth_wall(_resp(html, status=200)) is False


# --- JSON-LD ----------------------------------------------------------------

def test_extract_jsonld_jobs():
    html = """<html><head><script type="application/ld+json">
    {"@type": "JobPosting", "title": "Staff Engineer",
     "hiringOrganization": {"name": "Acme"},
     "jobLocation": {"address": {"addressLocality": "Berlin", "addressCountry": "DE"}},
     "datePosted": "2026-06-01T00:00:00Z",
     "baseSalary": {"currency": "EUR", "value": {"minValue": 90000, "maxValue": 120000}}}
    </script></head></html>"""
    jobs = extract_jsonld_jobs(html)
    assert len(jobs) == 1
    assert jobs[0].title == "Staff Engineer"
    assert jobs[0].company == "Acme"
    assert jobs[0].location == "Berlin, DE"
    assert jobs[0].date_posted == "2026-06-01"
    assert "90000" in jobs[0].salary


def test_extract_jsonld_bad_json_ignored():
    assert extract_jsonld_jobs('<script type="application/ld+json">{oops</script>') == []


# --- JS shell heuristic ------------------------------------------------------

def test_js_shell_detected():
    assert looks_like_js_shell('<html><body><div id="root"></div><script src="app.js"></script></body></html>')


def test_server_rendered_not_shell():
    words = " ".join(f"word{i}" for i in range(120))
    assert not looks_like_js_shell(f"<html><body><p>{words}</p></body></html>")


# --- validators --------------------------------------------------------------

def test_validate_jobs():
    ok, _ = validate_jobs([JobPosting(title="Eng", url="https://x.com/1")])
    assert ok
    assert not validate_jobs([])[0]
    assert not validate_jobs([JobPosting(title="")])[0]
    # titles but no url/location anywhere -> suspicious parse
    assert not validate_jobs([JobPosting(title="Eng")])[0]


def test_validate_fields():
    assert validate_fields({"price": "$10"}, ["price"])[0]
    assert not validate_fields({"price": None}, ["price"])[0]
    assert not validate_fields("nope", ["price"])[0]


def test_validate_page_info():
    assert validate_page_info({"summary": "A company.", "facts": {}})[0]
    assert not validate_page_info({"summary": "", "facts": {}})[0]


# --- LLM JSON parsing ----------------------------------------------------------

def test_extract_json_fenced():
    assert extract_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]


def test_extract_json_prose_wrapped():
    assert extract_json('Sure! Here it is: {"a": [1, 2], "b": "x}y"} hope that helps') == \
        {"a": [1, 2], "b": "x}y"}


def test_extract_json_none():
    assert extract_json("no json here") is None


# --- site-profile cache ----------------------------------------------------------

def test_cache_multi_tenant_keys(tmp_path):
    cache = SiteProfileCache(path=str(tmp_path / "p.json"))
    cache.put("https://job-boards.greenhouse.io/gitlab", "jobs",
              Recipe(tier=0, method="ats_api", params={"token": "gitlab"}))
    # same host, different tenant: must NOT share a recipe
    assert cache.get("https://job-boards.greenhouse.io/stripe", "jobs") is None
    assert cache.get("https://job-boards.greenhouse.io/gitlab", "jobs") is not None


def test_cache_invalidation_is_loud_and_sticky(tmp_path):
    cache = SiteProfileCache(path=str(tmp_path / "p.json"))
    cache.put("https://acme.com/careers", "jobs", Recipe(tier=1, method="static_llm"))
    cache.invalidate("https://acme.com/careers", "jobs", "expected field missing")
    assert cache.get("https://acme.com/careers", "jobs") is None
    raw = json.loads((tmp_path / "p.json").read_text())
    entry = raw["acme.com"]["jobs"]
    assert entry["stale"] is True
    assert entry["stale_reason"] == "expected field missing"


def test_cache_normal_domain_key(tmp_path):
    cache = SiteProfileCache(path=str(tmp_path / "p.json"))
    cache.put("https://acme.com/careers", "jobs", Recipe(tier=1, method="static_llm"))
    # same domain, different path -> same profile (per-domain recipes)
    assert cache.get("https://acme.com/jobs", "jobs") is not None


# --- strict field validation + partials (added after validation run 1) -------

def test_validate_fields_requires_all():
    ok, why = validate_fields({"price": "$10", "email": None}, ["price", "email"])
    assert not ok and "email" in why


def test_validate_page_info_question():
    data = {"summary": "A page.", "facts": {"x": 1}, "answer": None}
    assert not validate_page_info(data, has_question=True)[0]
    assert validate_page_info(data, has_question=False)[0]


def test_partial_score():
    from webaccess.router import _partial_score
    from webaccess.types import Task
    t = Task(kind="fields", fields=["a", "b", "c"])
    assert _partial_score({"a": 1, "b": None, "c": ""}, t) == 1
    assert _partial_score(None, t) == 0
