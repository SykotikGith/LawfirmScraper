"""Batch round 3.

Two firms are now essentially just CustomHTMLAdapter selector-tuning --
Sullivan & Cromwell (a.viewJobLink) and Squire Patton Boggs
(a.jobMoreDetailCaptionStyle) both showed real server-rendered job data in
round 2. This dumps each matched link's own text plus its parent row's
full text, to see exactly what the title/location text looks like and
whether a location_selector is findable.

The other three (Venable/ADP, Sheppard Mullin/FloRecruit, Paul Weiss/Taleo
Enterprise) still need an actual data endpoint:
- Paul Weiss: round 2 showed the *search form* page, not results -- Taleo
  Enterprise usually executes search via a REST call keyed by a numeric
  career-section ID embedded somewhere in the page's JS config. This
  greps for that.
- Venable: re-greps the ADP main.js bundle for *relative* API paths
  (previous round only caught absolute https:// URLs and found nothing
  useful).
- Sheppard Mullin: round 2's __NEXT_DATA__ was an empty static-export
  shell (real data fetched client-side after load) -- this pulls the
  page's actual JS bundle list and greps those for API path patterns.

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


# --- Sullivan & Cromwell: dump viewJobLink rows ----------------------------
def check_sullivan_cromwell() -> None:
    section("Sullivan & Cromwell -- dumping a.viewJobLink rows")
    url = "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=SULLCROM&cws=38"
    resp = fetch(url)
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    links = soup.select("a.viewJobLink")
    print(f"  a.viewJobLink count: {len(links)}")
    for link in links[:6]:
        row = link.find_parent(["tr", "li", "div"])
        row_text = row.get_text(" | ", strip=True)[:300] if row else "(no parent row found)"
        print(f"  --- link text: {link.get_text(strip=True)!r}")
        print(f"      href: {link.get('href')}")
        print(f"      parent <{row.name if row else '?'}> text: {row_text}")


# --- Squire Patton Boggs: dump jobMoreDetailCaptionStyle rows --------------
def check_squire_patton_boggs() -> None:
    section("Squire Patton Boggs -- dumping a.jobMoreDetailCaptionStyle rows")
    url = (
        "https://fsr.cvmailuk.com/spb/main.cfm?page=jobBoard&rcd=1309578"
        "&srxksl=1&groupType_21=5039&filter="
    )
    resp = fetch(url)
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    links = soup.select("a.jobMoreDetailCaptionStyle")
    print(f"  a.jobMoreDetailCaptionStyle count: {len(links)}")
    for link in links[:6]:
        row = link.find_parent("tr")
        row_text = row.get_text(" | ", strip=True)[:300] if row else "(no parent <tr> found)"
        print(f"  --- link text: {link.get_text(strip=True)!r}")
        print(f"      href: {link.get('href')}")
        print(f"      parent <tr> text: {row_text}")


# --- Paul Weiss: hunt for a Taleo career-section numeric ID ----------------
def check_paul_weiss() -> None:
    section("Paul Weiss -- hunting for Taleo career-section ID / REST config")
    url = "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl"
    resp = fetch(url)
    if resp is None:
        return
    for pattern in [
        r"careerSection[A-Za-z]*\s*[:=]\s*['\"]?(\d+)",
        r"csNo\s*[:=]\s*['\"]?(\d+)",
        r"portal\s*[:=]\s*['\"]?(\d+)",
        r"orgId\s*[:=]\s*['\"]?(\w+)",
    ]:
        hits = re.findall(pattern, resp.text)
        print(f"  pattern {pattern!r}: {sorted(set(hits))[:10]}")

    # Career section number is often embedded right in the URL path segment
    # after /careersection/ on internal links (e.g. /careersection/2/...).
    cs_paths = re.findall(r"/careersection/(\w+)/", resp.text)
    print(f"  /careersection/<x>/ path segments: {sorted(set(cs_paths))[:10]}")


# --- Venable: re-grep ADP bundle for relative API paths --------------------
def check_venable() -> None:
    section("Venable -- re-checking ADP main.js for relative API paths")
    resp = fetch("https://myjobs.cf.adp.com/main.9b686673fecb1b74.js")
    if resp is None:
        return
    if resp.status_code != 200:
        print(f"  status={resp.status_code} (bundle hash may have changed -- skip)")
        return
    for pattern_label, pattern in [
        ("relative /api/ or /cx/ paths", r'"(/(?:api|cx)[^"]{0,80})"'),
        ("graphql mentions", r'"[^"]{0,40}graphql[^"]{0,40}"'),
        ("environment.* config keys", r'\b(environment\.\w+)\s*[:=]'),
        ("apiUrl/baseUrl/endpoint keys", r'"(apiUrl|baseUrl|endpoint|restEndpoint)"\s*:\s*"([^"]{0,120})"'),
    ]:
        hits = re.findall(pattern, resp.text)
        print(f"  [{pattern_label}]: {len(hits)} hits, sample: {sorted(set(str(h) for h in hits))[:15]}")


# --- Sheppard Mullin: find and grep the real JS bundle ---------------------
def check_sheppard_mullin() -> None:
    section("Sheppard Mullin -- listing JS bundles, grepping for API paths")
    url = "https://florecruit.com/v2/app/sheppardbusinessservices/jobs"
    resp = fetch(url)
    if resp is None:
        return
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
    print(f"  script src count: {len(scripts)}")
    for s in scripts:
        print(f"    {s}")

    for s in scripts:
        if "_app" in s or "jobs" in s or "chunks" in s:
            full = s if s.startswith("http") else f"https://florecruit.com{s}"
            bundle = fetch(full)
            if bundle is None or bundle.status_code != 200:
                continue
            api_hits = re.findall(r'"(/api/[^"]{0,80})"', bundle.text)
            v2_hits = re.findall(r'"(https?://[^"]*florecruit[^"]{0,80})"', bundle.text)
            if api_hits or v2_hits:
                print(f"  [{full}] /api/ hits: {sorted(set(api_hits))[:10]}")
                print(f"  [{full}] florecruit URL hits: {sorted(set(v2_hits))[:10]}")


def main() -> None:
    check_sullivan_cromwell()
    check_squire_patton_boggs()
    check_paul_weiss()
    check_venable()
    check_sheppard_mullin()


if __name__ == "__main__":
    main()
