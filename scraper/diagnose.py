"""Round 5 (final) -- just Ogletree Deakins left. Round 4 confirmed
totalCount=148 and that page=N (not start/offset) is the real pagination
param. This gets the FULL, untruncated schema of one job record (round
3's dump was cut off before a location field, if one exists) and checks
that page=15 (the last full page) and page=16 (should be empty/short)
both behave as expected before trusting the pagination sweep end-to-end.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def fetch(url: str, method: str = "GET", **kwargs) -> requests.Response | None:
    try:
        if method == "GET":
            return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
        return requests.post(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return None


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    section("Ogletree Deakins -- full untruncated schema of one job")
    resp = fetch("https://careers.ogletree.com/api/jobs")
    if resp is None:
        return
    data = resp.json()
    jobs = data.get("jobs", [])
    if jobs:
        job_data = jobs[0].get("data", {})
        print(f"  all field names: {list(job_data.keys())}")
        # print everything except the long description field
        trimmed = {k: v for k, v in job_data.items() if k != "description"}
        print(json.dumps(trimmed, indent=2))

    section("Ogletree Deakins -- pagination sweep boundary check (page=15, page=16)")
    for page in [15, 16]:
        r = fetch("https://careers.ogletree.com/api/jobs", params={"page": page})
        if r is None:
            continue
        d = r.json()
        jobs_page = d.get("jobs", [])
        titles = [j.get("data", {}).get("title") for j in jobs_page]
        print(f"  page={page} -> jobs returned={len(jobs_page)} titles={titles}")


if __name__ == "__main__":
    main()
