"""Diagnostic: verify 2 new Workday leads (Troutman Pepper Locke, Fenwick
& West), plus check whether White & Case's newer myworkdaysite.com URL
format still works with our existing WorkdayAdapter (which assumes the
older {tenant}.{pod}.myworkdayjobs.com pattern) by hitting the same
underlying CXS API directly.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS
from .adapters.workday import WorkdayAdapter

TIMEOUT = 30


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


def check_white_case_new_domain() -> None:
    print("\n=== White & Case: myworkdaysite.com front-end vs. underlying CXS API ===")
    front_end = "https://wd1.myworkdaysite.com/recruiting/whitecase/External"
    resp = requests.get(front_end, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"  front-end {front_end}: status={resp.status_code} len={len(resp.text)}")

    # Test whether the OLD-style tenant subdomain + standard CXS API path
    # still works underneath, same as every other confirmed Workday firm.
    api_url = "https://whitecase.wd1.myworkdayjobs.com/wday/cxs/whitecase/External/jobs"
    body = {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": ""}
    api_resp = requests.post(api_url, headers=DEFAULT_HEADERS, json=body, timeout=TIMEOUT)
    print(f"  API {api_url}: status={api_resp.status_code}")
    print(f"    body[:400]: {api_resp.text[:400]!r}")


def main() -> None:
    check_workday("Troutman Pepper Locke", "troutman", "wd5", "TPRecruit1")
    check_workday("Fenwick & West", "fenwick", "wd1", "Fenwick_External_Careers")
    check_white_case_new_domain()


if __name__ == "__main__":
    main()
