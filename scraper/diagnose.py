"""Verification round for the 3 remaining real hits from the broad
42-firm ATS sniff: Faegre Drinker (Workday), Bryan Cave Leighton Paisner
(viGlobal), Davis Wright Tremaine (Jobvite).

Faegre Drinker: the embedded link found was
https://esswd.wd501.myworkdayjobs.com/External -- tenant="esswd",
pod="wd501", site="External". Neither matches the "faegredrinker" slug
guess or the wd1-wd10/103/115 pods ats_probe.py checked, which is exactly
why the earlier sweep missed it. Fetches real postings via the existing
WorkdayAdapter to confirm identity before trusting it.

Bryan Cave Leighton Paisner: the embedded link found
(bclplaw-careers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx
?FilterREID=55&FilterJobCategoryID=3&FilterJobID=430) is a single
filtered job, not the general listing page ViGlobalAdapter needs. Tries
the bare RecDefault.aspx URL (no query params) to see if it renders the
full unfiltered listing, the same shape O'Melveny & Myers' real list_url
has.

Davis Wright Tremaine: the embedded link found
(https://jobs.jobvite.com/dwt/) is a new platform for this project.
Fetches it to see whether it's server-rendered (scrapable like the
existing adapters) or a client-side SPA, and looks for any embedded
JSON/API references before deciding whether a new adapter is worth
building.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS
from .adapters.workday import WorkdayAdapter

TIMEOUT = 20


def check_faegre_drinker() -> None:
    print("=== Faegre Drinker (Workday: esswd / wd501 / External) ===")
    adapter = WorkdayAdapter("Faegre Drinker", {"tenant": "esswd", "wd": "wd501", "site": "External"})
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        print(f"  FETCH FAILED: {type(exc).__name__}: {exc}")
        return
    print(f"  {len(postings)} postings")
    for p in postings[:8]:
        print(f"    - {p.title} — {p.location}")


def check_bclp() -> None:
    print("\n=== Bryan Cave Leighton Paisner (viGlobal) ===")
    candidates = [
        "https://bclplaw-careers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx",
        "https://bclplaw-careers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx?FilterREID=55",
    ]
    for url in candidates:
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        except requests.exceptions.RequestException as exc:
            print(f"  {url}: EXCEPTION {type(exc).__name__}: {exc}")
            continue
        has_grid = "contentPlaceHolder_gridviewList" in resp.text
        row_count = resp.text.count("rowContainerHolder") if has_grid else 0
        print(f"  {url}\n    status={resp.status_code} len={len(resp.text)} "
              f"has_gridview_table={has_grid} rowContainerHolder_count={row_count}")
        if has_grid:
            # pull a small sample of visible row text to sanity check content
            idx = resp.text.find("contentPlaceHolder_gridviewList")
            print(f"    snippet near table: ...{resp.text[idx:idx+600]}...")


def check_dwt() -> None:
    print("\n=== Davis Wright Tremaine (Jobvite) ===")
    url = "https://jobs.jobvite.com/dwt/"
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return
    text = resp.text
    print(f"  status={resp.status_code}  final_url={resp.url}  len={len(text)}")

    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    print(f"  <script src> tags ({len(script_srcs)}):")
    for src in script_srcs[:15]:
        print(f"    {src}")

    api_hints = re.findall(r'["\'](/[\w./-]*(?:api|search|job)[\w./-]*)["\']', text, re.IGNORECASE)
    print(f"  possible API path fragments: {sorted(set(api_hints))[:20]}")

    job_link_count = len(re.findall(r'/job/', text, re.IGNORECASE))
    print(f"  '/job/' occurrences in raw HTML: {job_link_count}")

    print("  first 1500 chars of body:")
    print(f"  {text[:1500]!r}")


def main() -> None:
    check_faegre_drinker()
    check_bclp()
    check_dwt()


if __name__ == "__main__":
    main()
