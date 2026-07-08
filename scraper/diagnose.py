"""Round 4 diagnostic -- last three holdouts.

- Marshall Dennehey: /careers is a marketing shell and wp-json 404'd (not a
  standard WordPress REST install despite the Great Jakes CMS comment).
  Individual job pages clearly exist (confirmed by research at URLs like
  /careers/associate-attorney-...-orlando-fl), so try the sitemap instead
  of hunting for an index page.
- Fisher Phillips: page has "reqResult"/"ReqRowClick" CSS classes (real
  ClearCompany/HRM Direct scaffolding) but zero matches for job links in
  round 2/3 -- check whether rows exist further down the page, or whether
  results load via a separate AJAX call.
- Reed Smith: URL shape (/jobs/vacancy/find/results, /jobs/custom/<client>_02/)
  strongly resembles the Eploy ATS. Try common Eploy AJAX/JSON result
  variants of the same URL.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def marshall_dennehey() -> None:
    print("\n=== Marshall Dennehey: sitemap hunt ===")
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/careers-sitemap.xml", "/page-sitemap.xml"]:
        url = f"https://www.marshalldennehey.com{path}"
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        print(f"{path}: status={resp.status_code} content-type={resp.headers.get('content-type')} len={len(resp.text)}")
        if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
            locs = re.findall(r"<loc>([^<]+)</loc>", resp.text)
            careers_locs = [l for l in locs if "career" in l.lower()]
            print(f"  {len(locs)} <loc> entries total, {len(careers_locs)} mention 'career':")
            for l in careers_locs[:15]:
                print("   ", l)
            sub_sitemaps = [l for l in locs if "sitemap" in l.lower()]
            if sub_sitemaps:
                print(f"  sub-sitemaps referenced: {sub_sitemaps[:10]}")


def fisher_phillips() -> None:
    print("\n=== Fisher Phillips: full reqResult usage scan ===")
    url = "https://fisherphillips.hrmdirect.com/employment/job-openings.php"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    # Look past the <style> block for actual usage, not just the CSS rule.
    body_start = text.find("</style>")
    body = text[body_start:] if body_start != -1 else text
    print(f"'reqResult' usages after </style>: {body.count('reqResult')}")
    print(f"'ReqRowClick' usages after </style>: {body.count('ReqRowClick')}")
    idx = body.find("reqResult")
    if idx != -1:
        print("context around first post-style 'reqResult':")
        print(" ", body[max(0, idx - 200):idx + 400].replace("\n", " "))
    # Look for any <script> that fetches job data dynamically.
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL)
    ajaxy = [s for s in scripts if re.search(r"\.load\(|\$\.get|\$\.post|fetch\(|XMLHttpRequest", s)]
    print(f"scripts with AJAX-looking calls: {len(ajaxy)}")
    for s in ajaxy[:3]:
        print("  ", s.strip()[:300].replace("\n", " "))


def reed_smith() -> None:
    print("\n=== Reed Smith: Eploy-style AJAX/JSON variants ===")
    candidates = [
        "https://careers.reedsmith.com/jobs/vacancy/find/results?format=json",
        "https://careers.reedsmith.com/jobs/vacancy/find/results.json",
        "https://careers.reedsmith.com/jobs/vacancy/find/resultsdata",
        "https://careers.reedsmith.com/jobs/vacancy/find/results/ajax",
        "https://careers.reedsmith.com/jobs/vacancy/search",
        "https://careers.reedsmith.com/jobs/api/vacancy/search",
    ]
    for url in candidates:
        try:
            resp = requests.get(
                url,
                headers={**DEFAULT_HEADERS, "X-Requested-With": "XMLHttpRequest"},
                timeout=TIMEOUT,
            )
            print(f"{url}: status={resp.status_code} content-type={resp.headers.get('content-type')} "
                  f"len={len(resp.text)}")
            if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
                print("  body snippet:", resp.text[:400])
        except Exception as exc:  # noqa: BLE001
            print(f"{url}: EXCEPTION {type(exc).__name__}: {exc}")

    # Also check whether the results page differs when given an empty POST
    # (some Eploy sites render server-side only on POST with a filter body).
    try:
        resp = requests.post(
            "https://careers.reedsmith.com/jobs/vacancy/find/results",
            headers=DEFAULT_HEADERS,
            data={},
            timeout=TIMEOUT,
        )
        print(f"POST /jobs/vacancy/find/results: status={resp.status_code} len={len(resp.text)}")
        print(f"  'vacancy-result' or 'VacancyId' occurrences: "
              f"{resp.text.count('vacancy-result')} / {resp.text.count('VacancyId')}")
    except Exception as exc:  # noqa: BLE001
        print(f"POST attempt: EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    marshall_dennehey()
    fisher_phillips()
    reed_smith()


if __name__ == "__main__":
    main()
