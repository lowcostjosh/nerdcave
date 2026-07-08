"""Deterministic field-accuracy diff: pipeline page-extraction vs ATS API
ground truth. No LLM involved. Produces validation/ats_group.json."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
FIELDS = ["title", "location", "company", "url", "date_posted", "salary", "department"]
SAMPLE = 10


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def gt_jobs(site, platform, raw):
    """Normalize raw API JSON to the pipeline's JobPosting shape."""
    out = []
    if platform == "greenhouse":
        for j in raw.get("jobs", []):
            out.append({
                "title": j.get("title", ""),
                "location": (j.get("location") or {}).get("name"),
                "company": j.get("company_name") or site,
                "url": j.get("absolute_url"),
                "date_posted": (j.get("updated_at") or "")[:10] or None,
                "salary": None,
                "department": ", ".join(d.get("name", "") for d in j.get("departments") or []) or None,
            })
    else:  # lever
        import datetime
        for j in raw:
            cats = j.get("categories") or {}
            sr = j.get("salaryRange")
            salary = f"{sr.get('currency','USD')} {sr['min']}-{sr.get('max','')}" if sr and sr.get("min") else None
            created = j.get("createdAt")
            out.append({
                "title": j.get("text", ""),
                "location": cats.get("location"),
                "company": site,
                "url": j.get("hostedUrl"),
                "date_posted": datetime.datetime.utcfromtimestamp(created/1000).strftime("%Y-%m-%d") if created else None,
                "salary": salary,
                "department": cats.get("team") or cats.get("department"),
            })
    return out


def field_match(field, got, want):
    """Lenient-but-honest comparison. None==None counts as api_null."""
    if want in (None, ""):
        return "api_null"
    if got in (None, ""):
        return "missing"
    g, w = norm(str(got)), norm(str(want))
    if field == "url":
        # compare path identity, ignoring scheme/tracking
        g = re.sub(r"[?#].*", "", str(got)).rstrip("/")
        w = re.sub(r"[?#].*", "", str(want)).rstrip("/")
        return "correct" if g.lower() == w.lower() else "wrong"
    if field in ("location", "department", "salary"):
        # one containing the other is fine (page shows "Remote, USA",
        # API says "USA"), and multi-location pages vary in order
        gs, ws = set(g.split(",")) if "," in g else {g}, set(w.split(",")) if "," in w else {w}
        if g == w or g in w or w in g or (gs & ws):
            return "correct"
        return "wrong"
    return "correct" if g == w else "wrong"


def diff_site(site, platform, page_file, default_file, gt_file):
    page = json.loads((HERE / page_file).read_text())
    default = json.loads((HERE / default_file).read_text())
    gt_raw = json.loads((HERE / gt_file).read_text())
    gt = gt_jobs(site, platform, gt_raw)
    gt_by_title = {}
    for j in gt:
        gt_by_title.setdefault(norm(j["title"]), []).append(j)

    extracted = page.get("data") or []
    sample = extracted[:SAMPLE]
    acc = {f: {"correct": 0, "wrong": 0, "missing": 0, "api_null": 0} for f in FIELDS}
    mismatches = []
    unmatched = 0
    for e in sample:
        cands = gt_by_title.get(norm(e.get("title")))
        if not cands:
            unmatched += 1
            mismatches.append({"cause": "no_title_match_in_api", "extracted_title": e.get("title")})
            continue
        # disambiguate multi-location duplicates by location when possible
        g = cands[0]
        if len(cands) > 1 and e.get("location"):
            for c in cands:
                if field_match("location", e.get("location"), c.get("location")) == "correct":
                    g = c
                    break
        for f in FIELDS:
            verdict = field_match(f, e.get(f), g.get(f))
            acc[f][verdict] += 1
            if verdict == "wrong":
                mismatches.append({"cause": "field_mismatch", "field": f,
                                   "extracted": e.get(f), "api": g.get(f),
                                   "title": e.get("title")})

    return {
        "site": site, "platform": platform,
        "default_run": {k: default.get(k) for k in
                        ("tier_used", "method", "model_used", "latency_s", "tokens_used", "success")}
                       | {"count": len(default.get("data") or [])},
        "page_run": {k: page.get(k) for k in
                     ("tier_used", "method", "model_used", "latency_s", "tokens_used", "success", "status")}
                    | {"count": len(extracted)},
        "ground_truth_count": len(gt),
        "recall_page_run": round(len(extracted) / len(gt), 3) if gt else None,
        "default_matches_api_exactly": len(default.get("data") or []) == len(gt),
        "sample_size": len(sample),
        "unmatched_in_sample": unmatched,
        "field_accuracy": acc,
        "mismatch_examples": mismatches[:6],
    }


SITES = [
    ("gitlab", "greenhouse", "page_gitlab.json", "default_gitlab.json", "gt_gitlab.json"),
    ("stripe", "greenhouse", "page_stripe.json", "default_stripe.json", "gt_stripe.json"),
    ("anthropic", "greenhouse", "page_anthropic.json", "default_anthropic.json", "gt_anthropic.json"),
    ("palantir", "lever", "page_palantir.json", "default_palantir.json", "gt_palantir.json"),
    ("wealthfront", "lever", "page_wealthfront.json", "default_wealthfront.json", "gt_wealthfront.json"),
]

if __name__ == "__main__":
    results = []
    for args in SITES:
        try:
            results.append(diff_site(*args))
        except Exception as e:
            results.append({"site": args[0], "error": f"{type(e).__name__}: {e}"})
    (HERE / "ats_group.json").write_text(json.dumps(results, indent=2))
    for r in results:
        if "error" in r:
            print(f"{r['site']}: ERROR {r['error']}")
            continue
        d, p = r["default_run"], r["page_run"]
        print(f"\n{r['site']} ({r['platform']}), API total={r['ground_truth_count']}")
        print(f"  default: tier {d['tier_used']} {d['method']} -> {d['count']} jobs, "
              f"{d['latency_s']:.1f}s, {d['tokens_used']} tokens, exact={r['default_matches_api_exactly']}")
        print(f"  page:    tier {p['tier_used']} {p['method']} model={p['model_used']} -> "
              f"{p['count']} jobs (recall {r['recall_page_run']}), {p['latency_s']:.1f}s, {p['tokens_used']} tok")
        accs = []
        for f in FIELDS:
            a = r["field_accuracy"][f]
            denom = a["correct"] + a["wrong"] + a["missing"]
            if denom:
                accs.append(f"{f} {a['correct']}/{denom}")
        print(f"  fields:  {', '.join(accs)}  (unmatched {r['unmatched_in_sample']}/{r['sample_size']})")
