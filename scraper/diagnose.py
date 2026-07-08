"""Diagnostic: verify the 4 real ATS URLs found manually --
3 Workday (Paul Hastings, Cooley, Jackson Lewis) via the existing
WorkdayAdapter, and 1 new platform never seen in this project before:
Debevoise & Plimpton on "Circa Works" (circaworks.com). Circa Works needs
its own investigation -- fetch the page raw and see whether it's
server-rendered HTML (scrapable with CustomHTMLAdapter) or JS-driven
(needs its own adapter or a different approach).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS
from .adapters.workday import WorkdayAdapter

TIMEOUT = 20

WORKDAY_CHECKS = [
    ("Paul Hastings", "paulhastings", "wd1", "PH-Staff"),
    ("Cooley", "cooley", "wd1", "Cooley_US_LLP"),
    ("Jackson Lewis", "jacksonlewis", "wd1", "JacksonLewisBusinessandLegalProfessionalsCareers"),
]


def check_workday(firm: str, tenant: str, pod: str, site: str) -> None:
    print(f"\n=== {firm} (Workday {tenant}.{pod}, site={site}) ===")
    adapter = WorkdayAdapter(firm, {"tenant": tenant, "wd": pod, "site": site})
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        print(f"  FETCH FAILED: {type(exc).__name__}: {exc}")
        return
    print(f"  {len(postings)} postings")
    for p in postings[:6]:
        print(f"    - {p.title} — {p.location}")


def check_circaworks() -> None:
    print("\n=== Debevoise & Plimpton (Circa Works -- new platform) ===")
    url = "https://employer.circaworks.com/s/e-Debevoise-Plimpton-LLP-jobs-e87905.html?pbid=68216"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"  status={resp.status_code} len={len(resp.text)} content-type={resp.headers.get('content-type')}")
    text = resp.text
    print(f"  body[:800]: {text[:800]!r}")
    # Look for job-listing-shaped links/data in the raw HTML.
    import re
    job_hrefs = re.findall(r'href="([^"]*job[^"]*)"', text, re.IGNORECASE)
    print(f"  'job'-containing hrefs found (first 15 of {len(job_hrefs)}):")
    for h in job_hrefs[:15]:
        print(f"    {h}")
    # Check for an API/JSON reference (common for JS-driven boards).
    api_like = sorted(set(re.findall(r'["\']([^"\']*(?:/api/|\.json|/graphql)[^"\']*)["\']', text)))
    print(f"  api-like strings found (first 10 of {len(api_like)}):")
    for s in api_like[:10]:
        print(f"    {s}")


def main() -> None:
    for firm, tenant, pod, site in WORKDAY_CHECKS:
        check_workday(firm, tenant, pod, site)
    check_circaworks()


if __name__ == "__main__":
    main()
