"""Diagnostic: stop assuming Workday for Blank Rome and Covington &
Burling -- the word "workday" doesn't appear on either page at all,
despite both having a confirmed-real (but likely dormant, same as
Milbank/Debevoise/O'Melveny) Workday tenant. Extract every external
domain referenced anywhere on the page instead, to find whatever the
real ATS actually is without guessing.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

KNOWN_ATS_HINTS = [
    "icims", "myworkdayjobs", "myworkdaysite", "greenhouse.io", "applicantstack",
    "hrmdirect", "avature", "phenompeople", "oraclecloud", "smartrecruiters",
    "lever.co", "ultipro", "successfactors", "taleo", "pageuppeople", "circaworks",
    "viglobalcloud", "clearcompany", "jazzhr", "bamboohr", "workable", "breezy",
    "jobvite", "cornerstoneondemand", "adp.com", "recruiterbox",
]


def dump_external_domains(label: str, url: str) -> None:
    print(f"\n=== {label}: {url} ===")
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"status={resp.status_code} len={len(resp.text)}")
    soup = BeautifulSoup(resp.text, "lxml")
    own_host = urlparse(url).netloc

    domains: dict[str, list[str]] = {}
    for tag, attr in [("a", "href"), ("iframe", "src"), ("script", "src"), ("link", "href")]:
        for el in soup.find_all(tag):
            val = el.get(attr)
            if not val or not val.startswith("http"):
                continue
            host = urlparse(val).netloc
            if not host or own_host in host or host in own_host:
                continue
            domains.setdefault(host, []).append(val)

    print(f"{len(domains)} distinct external domain(s) referenced:")
    for host, urls in sorted(domains.items()):
        hint_hit = next((h for h in KNOWN_ATS_HINTS if h in host.lower()), None)
        marker = "  <-- KNOWN ATS PATTERN" if hint_hit else ""
        print(f"  {host} ({len(urls)} ref(s)){marker}")
        for u in urls[:2]:
            print(f"      {u}")

    # Also look for a "search jobs" / "view openings" / "current openings"
    # style link even if it stays same-domain (might be a sub-page we
    # haven't tried yet).
    candidates = [
        a.get("href") for a in soup.find_all("a")
        if a.get("href") and re.search(r"search|opening|opportunit|apply|current", a.get_text(" ", strip=True), re.IGNORECASE)
    ]
    print(f"\nsame-page links with 'search'/'opening'/'opportunit'/'apply'/'current' in their text "
          f"(first 10 of {len(candidates)}):")
    for c in candidates[:10]:
        print(f"  {c}")


def main() -> None:
    dump_external_domains("Blank Rome", "https://www.blankrome.com/careers/overview/business-professionals/")
    dump_external_domains(
        "Covington & Burling",
        "https://www.cov.com/en/careers/business-professionals/employment-opportunities",
    )


if __name__ == "__main__":
    main()
