"""Round 3: confirmed working CXS endpoint for Wachtell Lipton is
https://wd1.myworkdaysite.com/wday/cxs/vhr_wachtelllipton/wlrk/jobs (total=8,
real jobPostings, hit directly off the myworkdaysite.com domain rather than a
per-tenant subdomain -- the vhr_wachtelllipton tenant slug has an underscore,
which isn't valid in a real hostname/wildcard-cert, so the old-style
{tenant}.{wd}.myworkdayjobs.com subdomain SSL-fails).

Two things left to confirm before wiring this into config.py:

1. All 8 real posting titles/locations, to sanity-check this is genuinely
   Wachtell Lipton and not some unrelated tenant (only "Messenger" and
   "Imaging Technician" seen so far).
2. The job-detail URL pattern. The real recruiting URL the user gave uses
   /recruiting/{tenant}/{site} (not the old-style /en-US/{site}), so this
   tries building a full job URL as
   https://wd1.myworkdaysite.com/recruiting/vhr_wachtelllipton/wlrk<externalPath>
   and fetches it directly to confirm it resolves to a real job page (not a
   404/redirect-to-search-home).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20
CXS_URL = "https://wd1.myworkdaysite.com/wday/cxs/vhr_wachtelllipton/wlrk/jobs"
RECRUITING_BASE = "https://wd1.myworkdaysite.com/recruiting/vhr_wachtelllipton/wlrk"


def fetch(url: str, method: str = "GET", **kwargs) -> requests.Response | None:
    try:
        if method == "GET":
            return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
        return requests.post(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return None


def list_all_postings() -> list[dict]:
    print(f"=== fetching all postings from {CXS_URL} ===")
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    resp = fetch(CXS_URL, method="POST", json=body)
    if resp is None:
        return []
    print(f"  status={resp.status_code}")
    data = resp.json()
    postings = data.get("jobPostings", [])
    print(f"  total={data.get('total')}  jobPostings returned={len(postings)}")
    for job in postings:
        print(f"    - {job.get('title')!r} | {job.get('locationsText')!r} | {job.get('externalPath')!r} | {job.get('postedOn')!r}")
    return postings


def check_job_detail_url(postings: list[dict]) -> None:
    if not postings:
        print("\n(no postings to test a detail URL against)")
        return
    print("\n=== testing job-detail URL pattern ===")
    for job in postings[:3]:
        external_path = job.get("externalPath", "")
        url = f"{RECRUITING_BASE}{external_path}"
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url}\n    status={resp.status_code}  final_url={resp.url}  len={len(resp.text)}")
        title = job.get("title", "")
        print(f"    title {'FOUND' if title and title in resp.text else 'NOT FOUND'} in page body")


def main() -> None:
    postings = list_all_postings()
    check_job_detail_url(postings)


if __name__ == "__main__":
    main()
