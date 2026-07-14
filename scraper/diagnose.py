"""Batch round: 8 new firm leads (Baker Botts dropped per explicit
instruction -- confirmed attorney-only, no diagnostic needed).

High confidence (reusing already-proven adapters, just need real-data
confirmation): 2 UltiPro (Hunton Andrews Kurth, Eversheds Sutherland),
1 Workday (Munger Tolles), 1 Taleo Business Edition on the exact same
host already proven for Sullivan & Cromwell (Katten Muchin Rosenman),
1 viGlobal on the firm's own domain, same URL shape as Winston Taylor
(Mintz Levin).

New/unclear: Arnold & Porter (own domain, unresearched platform), Dechert
(hash-anchor career page, same pattern as Duane Morris), Akin Gump
(SilkRoad again but a different URL shape than WilmerHale's --
jobs.silkroad.com/<company>/<company> instead of
<company>-openhire.silkroad.com/epostings/...).

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


# --- UltiPro pair -------------------------------------------------------
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


# --- Workday (Munger Tolles) ---------------------------------------------
def check_munger_tolles() -> None:
    section("Munger Tolles -- Workday CXS, tenant=mto wd=wd503 site=MTO_Careers")
    prime = fetch("https://mto.wd503.myworkdayjobs.com/MTO_Careers")
    if prime:
        print(f"  prime GET: status={prime.status_code} len={len(prime.text)}")
    api_url = "https://mto.wd503.myworkdayjobs.com/wday/cxs/mto/MTO_Careers/jobs"
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


# --- Taleo Business Edition (Katten Muchin Rosenman) ----------------------
def check_katten() -> None:
    section("Katten Muchin Rosenman -- Taleo Business Edition (same host as Sullivan & Cromwell)")
    url = "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=KATTMUCH2&cws=39"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    links = soup.select("a.viewJobLink")
    print(f"  a.viewJobLink count: {len(links)}")
    for link in links[:10]:
        row = link.find_parent(["tr", "li", "div"])
        row_text = row.get_text(" | ", strip=True)[:200] if row else "(no row)"
        print(f"    {link.get_text(strip=True)!r} | row: {row_text}")


# --- viGlobal (Mintz Levin) -----------------------------------------------
def check_mintz_levin() -> None:
    section("Mintz Levin -- viGlobal on careers.mintz.com")
    url = "https://careers.mintz.com/viRecruitSelfApply/RecDefault.aspx?Tag=fdfa0684-8265-4911-aece-f31f96213ea9"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    has_default_table = "contentPlaceHolder_gridviewList" in resp.text
    other_tables = re.findall(r'<table[^>]*id="([^"]+)"', resp.text)
    print(f"  default gridviewList table present: {has_default_table}")
    print(f"  all table ids found: {other_tables[:10]}")
    h4_titles = re.findall(r"<h4[^>]*>([^<]+)</h4>", resp.text)
    print(f"  <h4> texts found: {h4_titles[:10]}")


# --- Arnold & Porter (unclear) --------------------------------------------
def check_arnold_porter() -> None:
    section("Arnold & Porter -- structural inspection")
    url = "https://www.arnoldporter.com/en/careers/professional-staff/current-opportunities?skip=0&reload=false&scroll=0"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    script_srcs = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
    print(f"  script src count: {len(script_srcs)}; sample: {script_srcs[:8]}")
    api_hints = re.findall(r'"(/[a-zA-Z0-9_/.-]*api[a-zA-Z0-9_/.-]*)"', resp.text, re.I)
    print(f"  /api/-looking relative paths: {sorted(set(api_hints))[:10]}")
    job_like = re.findall(r'<(\w+)[^>]*\b(?:class|id)="([^"]*(?:job|opening|opportunit)[^"]*)"', resp.text, re.I)
    print(f"  job/opening/opportunity class or id hits: {len(job_like)}; sample: {job_like[:10]}")
    print(f"  body[:400]: {resp.text[:400]!r}")


# --- Dechert (unclear, hash anchor like Duane Morris) ---------------------
def check_dechert() -> None:
    section("Dechert -- structural inspection")
    url = "https://www.dechert.com/careers.html"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    script_srcs = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
    print(f"  script src count: {len(script_srcs)}; sample: {script_srcs[:8]}")
    job_like = re.findall(r'<(\w+)[^>]*\b(?:class|id)="([^"]*(?:job|opening|position)[^"]*)"', resp.text, re.I)
    print(f"  job/opening/position class or id hits: {len(job_like)}; sample: {job_like[:10]}")
    api_hints = re.findall(r'"(/[a-zA-Z0-9_/.-]*api[a-zA-Z0-9_/.-]*)"', resp.text, re.I)
    print(f"  /api/-looking relative paths: {sorted(set(api_hints))[:10]}")
    print(f"  body[:400]: {resp.text[:400]!r}")


# --- Akin Gump (SilkRoad, different URL shape than WilmerHale) ------------
def check_akin_gump() -> None:
    section("Akin Gump -- SilkRoad (jobs.silkroad.com/AkinGump/AkinGump)")
    url = "https://jobs.silkroad.com/AkinGump/AkinGump"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    job_links = re.findall(r'<a[^>]+href="([^"]*jobid=\d+[^"]*)"[^>]*>([^<]+)</a>', resp.text, re.I)
    print(f"  jobid= links found: {len(job_links)}")
    for href, text in job_links[:10]:
        print(f"    {text.strip()!r} -> {href}")
    forms = re.findall(r'<form[^>]*action="([^"]*)"[^>]*method="([^"]*)"', resp.text, re.I)
    print(f"  forms found: {forms}")
    print(f"  body[:400]: {resp.text[:400]!r}")


def main() -> None:
    check_ultipro("Hunton Andrews Kurth", "https://recruiting.ultipro.com/HUN1002HW/JobBoard/c54d0719-19af-46ae-b27a-8c3695a9ab0a/")
    check_ultipro("Eversheds Sutherland", "https://recruiting.ultipro.com/SUT1001EVSU/JobBoard/80eaa491-46d1-4ef3-93bb-2f523c2631c7/")
    check_munger_tolles()
    check_katten()
    check_mintz_levin()
    check_arnold_porter()
    check_dechert()
    check_akin_gump()


if __name__ == "__main__":
    main()
