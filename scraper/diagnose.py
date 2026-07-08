"""Round 3 diagnostic, following up on round 2 findings:

- Cozen O'Connor: the API returns a search-facets echo, not job data, unless
  `expand=requisitionList` is requested. Verify that fixes it.
- DLA Piper / Clyde & Co: `total` came back as 0 on every page after the
  first, even though jobPostings kept returning 20 results each time --
  classic symptom of an unauthenticated/session-less paginated call. Test
  whether priming a shared session with an initial GET to the HTML page
  before POSTing fixes it.
- Reed Smith: page is an Astro/Vue SPA (job list not in the initial HTML).
  Look for an iframe, inline JSON state, or a same-origin API path
  referenced by the JS bundles.
- Fisher Phillips: page had zero job links in the initial HTML. Look for an
  iframe or embedded API reference.
- Marshall Dennehey: site is built on Great Jakes (a WordPress-based legal
  marketing platform, per the HTML comment) -- probe its wp-json REST API
  for a careers/jobs route.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def cozen_oconnor() -> None:
    print("\n=== Cozen O'Connor: retry with expand=requisitionList ===")
    url = (
        "https://hctq.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
        "recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
        "&finder=findReqs;siteNumber=CX_1,limit=100"
    )
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"status={resp.status_code}")
    data = resp.json()
    items = data.get("items", [])
    if not items:
        print("no items returned")
        return
    req_list = items[0].get("requisitionList")
    if req_list is None:
        print("items[0] still has no 'requisitionList' key. Full key list:", list(items[0].keys()))
        return
    print(f"requisitionList: len={len(req_list)}")
    if req_list:
        print("first job keys:", list(req_list[0].keys()))
        print("first job sample:", json.dumps(req_list[0], indent=2)[:1000])


def workday_session_primed_trace(label: str, tenant: str, wd: str, site: str) -> None:
    print(f"\n=== {label}: pagination trace WITH a primed session ===")
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    html_url = f"https://{tenant}.{wd}.myworkdayjobs.com/{site}"
    priming_resp = session.get(html_url, timeout=TIMEOUT)
    print(f"priming GET {html_url}: status={priming_resp.status_code}, "
          f"cookies set={list(session.cookies.keys())}")

    api_url = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    offset = 0
    limit = 20
    for page in range(6):
        body = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        resp = session.post(api_url, json=body, timeout=TIMEOUT)
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"  offset={offset}: status={resp.status_code} non-JSON body: {resp.text[:200]}")
            break
        n = len(data.get("jobPostings", []))
        total = data.get("total")
        titles = [j.get("title") for j in data.get("jobPostings", [])[:2]]
        print(f"  offset={offset}: status={resp.status_code} total={total} "
              f"jobPostings_returned={n} sample_titles={titles}")
        if n == 0:
            break
        offset += limit


def reed_smith() -> None:
    print("\n=== Reed Smith: looking for iframe / inline state / API refs ===")
    url = "https://careers.reedsmith.com/jobs/vacancy/find/results"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', text)
    print(f"iframes: {iframes}")
    inline_json_scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>', text)
    print(f"inline application/json script tags: {len(inline_json_scripts)}")
    # Look for same-origin API-ish paths mentioned anywhere in the HTML (not just <a href>)
    api_like = sorted(set(re.findall(r'["\']([^"\']*(?:/api/|\.json|/graphql)[^"\']*)["\']', text)))
    print(f"api-like string literals found in HTML (first 20 of {len(api_like)}):")
    for s in api_like[:20]:
        print(" ", s)
    # Fetch the first same-origin _astro JS bundle and grep it for API path hints
    js_paths = re.findall(r'src="(/jobs/custom/[^"]+\.js[^"]*)"', text)
    if js_paths:
        js_url = "https://careers.reedsmith.com" + js_paths[0].split('"')[0]
        print(f"fetching first JS bundle for inspection: {js_url}")
        js_resp = requests.get(js_url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        js_text = js_resp.text
        hints = sorted(set(re.findall(r'["\']([^"\']{0,80}(?:/api/|\.json|/graphql|/jobs/)[^"\']{0,40})["\']', js_text)))
        print(f"  API-like strings in that bundle (first 20 of {len(hints)}):")
        for h in hints[:20]:
            print("   ", h)


def fisher_phillips() -> None:
    print("\n=== Fisher Phillips: looking for iframe / API refs ===")
    url = "https://fisherphillips.hrmdirect.com/employment/job-openings.php"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', text)
    print(f"iframes: {iframes}")
    tables = re.findall(r"<table[^>]*>", text)
    print(f"<table> tags found: {len(tables)}")
    # Print a slice around the first occurrence of a plausible listing container
    for marker in ["job-title", "joblist", "job_list", "listing", "opening"]:
        idx = text.lower().find(marker)
        if idx != -1:
            print(f"found marker '{marker}' at {idx}:")
            print(" ", text[max(0, idx - 100):idx + 200].replace("\n", " "))
            break


def marshall_dennehey() -> None:
    print("\n=== Marshall Dennehey: probing wp-json (Great Jakes = WordPress) ===")
    resp = requests.get("https://www.marshalldennehey.com/wp-json/", headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"GET /wp-json/ status={resp.status_code} content-type={resp.headers.get('content-type')}")
    if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
        data = resp.json()
        routes = list(data.get("routes", {}).keys())
        job_related = [r for r in routes if any(k in r.lower() for k in ["job", "career", "posting", "position"])]
        print(f"total routes: {len(routes)}")
        print(f"job/career-related routes: {job_related}")
    else:
        print(resp.text[:500])


def main() -> None:
    cozen_oconnor()
    workday_session_primed_trace("DLA Piper", "dlapiper", "wd1", "dlapiper")
    workday_session_primed_trace("Clyde & Co US", "clydeco", "wd103", "clydecocareers")
    reed_smith()
    fisher_phillips()
    marshall_dennehey()


if __name__ == "__main__":
    main()
