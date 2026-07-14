"""Batch round: 14 new firm leads (Blank Rome explicitly excluded per user
instruction -- staying manual, no automation attempt).

Grouped by confidence:
- HIGH (reusing already-proven adapters/platforms, just need real-data
  confirmation): 3 UltiPro (Baker Hostetler, Fox Rothschild, Baker
  Donelson), 2 viGlobal (Bracewell, Jones Day), 1 Workday (Hogan
  Lovells).
- NEW PLATFORM for this project: Marshall Dennehey on Breezy HR --
  Breezy career sites commonly expose a public /json endpoint.
- iCIMS tenant confirmation only (Latham & Watkins, Mayer Brown) -- these
  will land in MANUAL_CHECK_FIRMS regardless (WAF-blocked like every
  other iCIMS tenant so far), just confirming the real tenant slug for
  documentation, same treatment as Willkie Farr & Gallagher.
- UNCLEAR platform, first-pass structural inspection needed: Kirkland &
  Ellis, Wilson Sonsini, WilmerHale (SilkRoad OpenHire), Ogletree
  Deakins, Duane Morris, Kramer Levin (now Herbert Smith Freehills
  Kramer, HSF Kramer career site).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

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


# --- UltiPro trio -----------------------------------------------------------
def check_ultipro(label: str, board_url: str) -> None:
    section(f"{label} -- UltiPro board {board_url}")
    search_url = f"{board_url.rstrip('/')}/JobBoardView/LoadSearchResults"
    body = {"opportunitySearch": {"Text": "", "Skip": 0, "Take": 20}}
    resp = fetch(search_url, method="POST", json=body)
    if resp is None:
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    if resp.status_code == 200:
        data = resp.json()
        opps = data.get("opportunities", [])
        print(f"  totalCount={data.get('totalCount')} returned={len(opps)}")
        for opp in opps[:10]:
            print(f"    - {opp.get('Title')!r}")


# --- viGlobal pair ------------------------------------------------------------
def check_viglobal(label: str, list_url: str) -> None:
    section(f"{label} -- viGlobal {list_url}")
    resp = fetch(list_url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    has_default_table = "contentPlaceHolder_gridviewList" in resp.text
    other_tables = re.findall(r'<table[^>]*id="([^"]+)"', resp.text)
    print(f"  default gridviewList table present: {has_default_table}")
    print(f"  all table ids found: {other_tables[:10]}")
    h4_titles = re.findall(r"<h4[^>]*>([^<]+)</h4>", resp.text)
    print(f"  <h4> texts found: {h4_titles[:10]}")


# --- Workday (Hogan Lovells) --------------------------------------------------
def check_hogan_lovells() -> None:
    section("Hogan Lovells -- Workday CXS, tenant=hoganlovells wd=wd3 site=Search")
    prime = fetch("https://hoganlovells.wd3.myworkdayjobs.com/Search")
    if prime:
        print(f"  prime GET: status={prime.status_code} len={len(prime.text)}")
    api_url = "https://hoganlovells.wd3.myworkdayjobs.com/wday/cxs/hoganlovells/Search/jobs"
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    resp = fetch(api_url, method="POST", json=body)
    if resp is None:
        return
    print(f"  CXS POST: status={resp.status_code} len={len(resp.text)}")
    if resp.status_code == 200:
        data = resp.json()
        postings = data.get("jobPostings", [])
        print(f"  total={data.get('total')} returned={len(postings)}")
        for job in postings[:10]:
            print(f"    - {job.get('title')!r} | {job.get('locationsText')!r}")


# --- Marshall Dennehey (Breezy HR, new platform) ------------------------------
def check_marshall_dennehey() -> None:
    section("Marshall Dennehey -- Breezy HR (marshall-dennehey.breezy.hr)")
    for url in [
        "https://marshall-dennehey.breezy.hr/json",
        "https://marshall-dennehey.breezy.hr/",
    ]:
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url} -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:400]: {resp.text[:400]!r}")


# --- iCIMS tenant confirmation only -------------------------------------------
def check_icims(label: str, search_url: str) -> None:
    section(f"{label} -- iCIMS tenant confirmation (expect WAF block either way)")
    resp = fetch(search_url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    print(f"  body[:300]: {resp.text[:300]!r}")


# --- Unclear-platform structural inspection -----------------------------------
def inspect_unclear(label: str, url: str) -> None:
    section(f"{label} -- structural inspection: {url}")
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    script_srcs = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
    print(f"  script src count: {len(script_srcs)}; sample: {script_srcs[:6]}")
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if next_data:
        print(f"  __NEXT_DATA__ found, length={len(next_data.group(1))}, sample: {next_data.group(1)[:300]!r}")
    api_hints = re.findall(r'"(/[a-zA-Z0-9_/.-]*api[a-zA-Z0-9_/.-]*)"', resp.text, re.I)
    print(f"  /api/-looking relative paths: {sorted(set(api_hints))[:10]}")
    job_like = re.findall(r'<(\w+)[^>]*\b(?:class|id)="([^"]*(?:job|position|opening)[^"]*)"', resp.text, re.I)
    print(f"  job/position/opening class or id hits: {len(job_like)}; sample: {job_like[:10]}")
    print(f"  body[:400]: {resp.text[:400]!r}")


def main() -> None:
    check_ultipro("Baker Hostetler", "https://recruiting.ultipro.com/BAK1005BKH/JobBoard/da65e963-280e-4c79-9743-c8622538c0ea/")
    check_ultipro("Fox Rothschild", "https://recruiting.ultipro.com/fox1001frllp/JobBoard/88a19d60-0e84-49c7-b754-509a756678e7/")
    check_ultipro("Baker Donelson", "https://recruiting2.ultipro.com/BAK1000/JobBoard/2f6b40a8-4e29-e740-a3db-cb1a1e4563b8/")

    check_viglobal("Bracewell", "https://bracewellselfapply.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx?Tag=a9725fb0-5ae5-4b9f-accd-4441e0d4ec4e")
    check_viglobal("Jones Day", "https://jonesdaystaffrecruitselfapply.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx?Tag=ab6501e1-c8b5-402c-8909-e3e6af6d4e73")

    check_hogan_lovells()
    check_marshall_dennehey()

    check_icims("Latham & Watkins", "https://careers-lw.icims.com/jobs/search?hashed=-625915638")
    check_icims("Mayer Brown", "https://globalcareers-mayerbrown.icims.com/jobs/search?hashed=124489139")

    inspect_unclear("Kirkland & Ellis", "https://staffjobsus.kirkland.com/jobs/search/")
    inspect_unclear("Wilson Sonsini", "https://careers.wsgr.com/openings/?_opening_type=82")
    inspect_unclear("WilmerHale", "https://wilmerhale-openhire.silkroad.com/epostings/index.cfm?version=2&company_id=16437")
    inspect_unclear("Ogletree Deakins", "https://careers.ogletree.com/jobs")
    inspect_unclear("Duane Morris", "https://www.duanemorris.com/site/careers.html")
    inspect_unclear("Kramer Levin (HSF Kramer)", "https://careers.hsfkramer.com/global/en/us/search-results")


if __name__ == "__main__":
    main()
