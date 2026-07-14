"""Batch round 2: deeper structural inspection of the 6 leads round 1
couldn't resolve from a single top-level fetch.

- Vinson & Elkins (viGlobal): round 1 found the table id is
  "contentPlaceHolder_dataGridMain", not the usual
  "contentPlaceHolder_gridviewList" -- ViGlobalAdapter already supports a
  configurable table_id, so this just dumps that table's actual row
  markup to see which of the two known row shapes (or a third, new one)
  applies.
- Venable (ADP myjobs): round 1 confirmed it's a client-side Angular app
  (myjobs.cf.adp.com bundles) with no API trace in the static HTML. This
  fetches the main JS bundle and greps it for embedded API base URLs.
- Sullivan & Cromwell (Taleo Business Edition), Squire Patton Boggs
  (CV-Mail UK), and Paul Weiss (Taleo Enterprise careersection) all
  returned substantial real HTML (82-126KB) in round 1 but the first 500
  chars were just boilerplate/whitespace -- this generically hunts for
  any element whose class/id mentions "job"/"req" and any href that looks
  like a job-detail link, across all three.
- Sheppard Mullin (FloRecruit/Next.js): checks specifically for an
  embedded __NEXT_DATA__ script tag, which Next.js server-rendering often
  populates with real initial-page data even when the visible UI is
  client-rendered.

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


def find_job_like_elements(html: str, label: str) -> None:
    class_id_hits = re.findall(
        r'<(\w+)[^>]*\b(?:class|id)="([^"]*(?:job|req)[^"]*)"[^>]*>', html, re.I
    )
    print(f"  [{label}] elements with job/req in class or id: {len(class_id_hits)}")
    for tag, attr in class_id_hits[:15]:
        print(f"    <{tag} .../{attr!r}>")

    href_hits = re.findall(r'href="([^"]*(?:job|req|detail)[^"]*)"', html, re.I)
    print(f"  [{label}] hrefs mentioning job/req/detail: {len(href_hits)}")
    for href in sorted(set(href_hits))[:15]:
        print(f"    {href}")


# --- Vinson & Elkins (viGlobal, dataGridMain table) -----------------------
def check_vinson_elkins() -> None:
    section("Vinson & Elkins -- inspecting contentPlaceHolder_dataGridMain table")
    url = (
        "https://portal.velaw.com/viDesktopEx/viRecruitSelfApply/ReDefault.aspx"
        "?Tag=bf5353fd-6c9b-41e3-a72f-7abd61690415"
    )
    resp = fetch(url)
    if resp is None:
        return
    match = re.search(
        r'<table[^>]*id="contentPlaceHolder_dataGridMain"[^>]*>(.*?)</table>',
        resp.text,
        re.DOTALL,
    )
    if not match:
        print("  table not found in re-fetch (unexpected)")
        return
    table_html = match.group(1)
    print(f"  table inner HTML length: {len(table_html)}")
    rows = re.findall(r"<tr.*?</tr>", table_html, re.DOTALL)
    print(f"  <tr> rows found: {len(rows)}")
    for row in rows[:5]:
        print(f"  --- row ---\n{row[:600]}\n")


# --- Venable (ADP myjobs) -- fetch main JS bundle for API base URL --------
def check_venable() -> None:
    section("Venable -- fetching ADP main.js bundle for embedded API URLs")
    resp = fetch("https://myjobs.cf.adp.com/main.9b686673fecb1b74.js")
    if resp is None:
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    if resp.status_code != 200:
        print("  (bundle hash in filename may have changed since round 1 -- ignore if 404)")
        return
    urls = re.findall(r'"(https?://[a-zA-Z0-9.\-]+/[^"]{0,80})"', resp.text)
    api_like = sorted({u for u in urls if "adp.com" in u or "api" in u.lower()})
    print(f"  candidate API/base URLs found: {len(api_like)}")
    for u in api_like[:25]:
        print(f"    {u}")


# --- Sullivan & Cromwell (Taleo Business Edition) --------------------------
def check_sullivan_cromwell() -> None:
    section("Sullivan & Cromwell -- hunting for job-listing markup in Taleo TBE HTML")
    url = "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=SULLCROM&cws=38"
    resp = fetch(url)
    if resp is None:
        return
    find_job_like_elements(resp.text, "S&C")
    mid = len(resp.text) // 3
    print(f"  body[{mid}:{mid + 800}]: {resp.text[mid:mid + 800]!r}")


# --- Squire Patton Boggs (CV-Mail UK) ---------------------------------------
def check_squire_patton_boggs() -> None:
    section("Squire Patton Boggs -- hunting for job-listing markup in CV-Mail HTML")
    url = (
        "https://fsr.cvmailuk.com/spb/main.cfm?page=jobBoard&rcd=1309578"
        "&srxksl=1&groupType_21=5039&filter="
    )
    resp = fetch(url)
    if resp is None:
        return
    find_job_like_elements(resp.text, "SPB")
    mid = len(resp.text) // 2
    print(f"  body[{mid}:{mid + 800}]: {resp.text[mid:mid + 800]!r}")


# --- Sheppard Mullin (FloRecruit) -- check for __NEXT_DATA__ ---------------
def check_sheppard_mullin() -> None:
    section("Sheppard Mullin -- checking for Next.js __NEXT_DATA__ script")
    url = "https://florecruit.com/v2/app/sheppardbusinessservices/jobs"
    resp = fetch(url)
    if resp is None:
        return
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL
    )
    if not match:
        print("  no __NEXT_DATA__ script tag found")
        find_job_like_elements(resp.text, "Sheppard Mullin")
        return
    blob = match.group(1)
    print(f"  __NEXT_DATA__ length: {len(blob)}")
    print(f"  blob[:1500]: {blob[:1500]!r}")


# --- Paul Weiss (Taleo Enterprise careersection) ----------------------------
def check_paul_weiss() -> None:
    section("Paul Weiss -- hunting for job-listing markup in Taleo Enterprise HTML")
    url = "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl"
    resp = fetch(url)
    if resp is None:
        return
    find_job_like_elements(resp.text, "Paul Weiss")
    mid = len(resp.text) // 2
    print(f"  body[{mid}:{mid + 800}]: {resp.text[mid:mid + 800]!r}")


def main() -> None:
    check_vinson_elkins()
    check_venable()
    check_sullivan_cromwell()
    check_squire_patton_boggs()
    check_sheppard_mullin()
    check_paul_weiss()


if __name__ == "__main__":
    main()
