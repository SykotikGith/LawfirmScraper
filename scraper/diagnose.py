"""Batch round 4 (likely final for this batch).

Sullivan & Cromwell: round 3 confirmed a.viewJobLink gives the real title
and its parent <div> contains location text too, but get_text() mashed
them together -- this dumps the raw HTML (not get_text) of that parent
div to find the actual location element/class for a CustomHTMLAdapter
location_selector.

Paul Weiss: round 3's guesses at a career-section numeric ID all came up
empty. Classic Taleo Enterprise (careersection/*.ftl, not the newer REST
career sites) often stashes its config in "TFS_"-prefixed JS globals --
last attempt at finding something submittable before parking this as
manual-check.

Venable: round 3 found /cx/rm/v1/core/identity and /cx/staffing/v2/...
paths in the ADP bundle but nothing that looks like a job *listing*
endpoint. Trying a short list of sibling-path guesses directly.

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


# --- Sullivan & Cromwell: raw HTML of the viewJobLink parent div ----------
def check_sullivan_cromwell() -> None:
    section("Sullivan & Cromwell -- raw HTML of a.viewJobLink parent rows")
    url = "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=SULLCROM&cws=38"
    resp = fetch(url)
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    links = soup.select("a.viewJobLink")
    print(f"  a.viewJobLink count: {len(links)}")
    for link in links[:3]:
        row = link.find_parent(["tr", "li", "div"])
        print(f"  --- parent <{row.name if row else '?'}> raw HTML ---")
        print(str(row)[:1200] if row else "(none)")
        print()


# --- Paul Weiss: hunt for TFS_-prefixed Taleo Enterprise JS globals -------
def check_paul_weiss() -> None:
    section("Paul Weiss -- hunting for TFS_ Taleo Enterprise JS config globals")
    url = "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl"
    resp = fetch(url)
    if resp is None:
        return
    tfs_hits = re.findall(r"(TFS_\w+)\s*[:=]", resp.text)
    print(f"  TFS_ globals assigned: {sorted(set(tfs_hits))[:20]}")
    form_actions = re.findall(r'<form[^>]+action="([^"]+)"', resp.text)
    print(f"  <form action=...>: {form_actions}")
    submit_hints = re.findall(r'submitJobSearch\w*\([^)]*\)', resp.text)
    print(f"  submitJobSearch call sites: {submit_hints[:5]}")


# --- Venable: try sibling-path guesses off the ADP cx paths found ---------
def check_venable() -> None:
    section("Venable -- probing sibling job-listing endpoint guesses")
    base = "https://myjobs.adp.com/venablebusinessprofessionalcareers"
    candidates = [
        f"{base}/cx/rm/v1/jobs",
        f"{base}/cx/rm/v2/jobs",
        f"{base}/cx/rm/v1/job-search",
        f"{base}/cx/rm/v1/staffing/job-requisitions",
        f"{base}/cx/staffing/v2/job-requisitions",
        f"{base}/cx/rm/v1/job-requisition",
    ]
    for url in candidates:
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url} -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:300]: {resp.text[:300]!r}")


def main() -> None:
    check_sullivan_cromwell()
    check_paul_weiss()
    check_venable()


if __name__ == "__main__":
    main()
