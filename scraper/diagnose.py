"""Round 2 for the 6 firms round 1 couldn't resolve from a single top-level
fetch:

- Marshall Dennehey (Breezy HR): the /json endpoint is real and returns
  data (confirmed round 1), but the one sample title shown was an
  attorney role -- need the full title list to confirm business-
  professional postings exist, plus a pretty-printed single record to
  see the full field schema (location object, description availability)
  before building a BreezyAdapter.
- Wilson Sonsini: real WordPress + FacetWP page, but round 1's generic
  job/position/opening class search only found template/plugin
  boilerplate, not actual job entries -- this looks specifically for the
  FacetWP results template and real posting links.
- WilmerHale (SilkRoad OpenHire): round 1 showed a search FORM
  (jobSearchButtonDiv, jobAgentLink), not results -- this checks the
  form's actual action/method and tries a same-page empty-search
  variant.
- Ogletree Deakins (Jibe/iCIMS): round 1 found the Jibe JS bundle host
  (assets.jibecdn.com/prod/ogletree/...) but no data API -- tries a few
  common Jibe REST endpoint conventions directly.
- Kramer Levin / HSF Kramer (Phenom People): round 1 found 162
  job/position-related class hits (very promising) but not the actual
  listing markup -- this looks specifically for Phenom's typical
  phs-job-* card classes and any embedded JSON.
- Duane Morris: round 1's body[:400] was just template boilerplate --
  this searches the FULL page text for real job-title-shaped content
  near the #tab_SupportStaffOpportunities anchor the user pointed at.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
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


def check_marshall_dennehey() -> None:
    section("Marshall Dennehey -- full Breezy HR title list + schema")
    resp = fetch("https://marshall-dennehey.breezy.hr/json")
    if resp is None:
        return
    data = resp.json()
    print(f"  total postings: {len(data)}")
    print("  all titles:")
    for item in data:
        print(f"    - {item.get('name')!r} | type={item.get('type', {}).get('name')}")
    print("\n  full schema of first record:")
    print(json.dumps(data[0], indent=2)[:2000])


def check_wilson_sonsini() -> None:
    section("Wilson Sonsini -- hunting for FacetWP results / real job entries")
    resp = fetch("https://careers.wsgr.com/openings/?_opening_type=82")
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    template = soup.select_one(".facetwp-template")
    print(f"  .facetwp-template found: {template is not None}")
    if template:
        print(f"  .facetwp-template inner text[:800]: {template.get_text(' | ', strip=True)[:800]!r}")
    links = soup.select("a[href*='/openings/']")
    print(f"  a[href*='/openings/'] count: {len(links)}")
    for link in links[:10]:
        print(f"    {link.get_text(strip=True)!r} -> {link.get('href')}")


def check_wilmerhale() -> None:
    section("WilmerHale -- inspecting SilkRoad search form action/method")
    resp = fetch("https://wilmerhale-openhire.silkroad.com/epostings/index.cfm?version=2&company_id=16437")
    if resp is None:
        return
    forms = re.findall(r'<form[^>]*action="([^"]*)"[^>]*method="([^"]*)"', resp.text, re.I)
    print(f"  forms found: {forms}")
    fuseaction_hints = re.findall(r'fuseaction=([\w.]+)', resp.text)
    print(f"  fuseaction= references: {sorted(set(fuseaction_hints))[:15]}")
    # Try the common SilkRoad "list all jobs" fuseaction directly
    for fa in ["app.joblist", "app.jobsearch", "app.searchjobs", "app.results"]:
        url = f"https://wilmerhale-openhire.silkroad.com/epostings/index.cfm?fuseaction={fa}&company_id=16437&version=2"
        r = fetch(url)
        if r is None:
            continue
        print(f"  fuseaction={fa} -> status={r.status_code} len={len(r.text)}")


def check_ogletree_deakins() -> None:
    section("Ogletree Deakins -- trying common Jibe REST endpoint conventions")
    candidates = [
        "https://ogletree.jibeapply.com/api/apply/v2/jobs?domain=ogletree.com&start=0&num=20",
        "https://careers.ogletree.com/api/apply/v2/jobs?domain=careers.ogletree.com&start=0&num=20",
        "https://app.jibecdn.com/api/apply/v2/jobs?domain=careers.ogletree.com&start=0&num=20",
        "https://careers.ogletree.com/api/jobs",
    ]
    for url in candidates:
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url} -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:300]: {resp.text[:300]!r}")


def check_kramer_levin() -> None:
    section("Kramer Levin (HSF Kramer) -- hunting for Phenom job-card markup")
    resp = fetch("https://careers.hsfkramer.com/global/en/us/search-results")
    if resp is None:
        return
    phs_hits = re.findall(r'class="([^"]*phs-job[^"]*)"', resp.text)
    print(f"  phs-job-* class hits: {len(phs_hits)}; sample: {sorted(set(phs_hits))[:10]}")
    json_ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', resp.text, re.DOTALL)
    print(f"  application/ld+json blocks found: {len(json_ld)}")
    for block in json_ld[:2]:
        print(f"    {block[:300]!r}")
    job_titles = re.findall(r'"jobTitle"\s*:\s*"([^"]+)"', resp.text)
    print(f"  \"jobTitle\": references: {sorted(set(job_titles))[:15]}")


def check_duane_morris() -> None:
    section("Duane Morris -- full-page search for real job-title content")
    resp = fetch("https://www.duanemorris.com/site/careers.html")
    if resp is None:
        return
    tab = re.search(r'id="tab_SupportStaffOpportunities"[^>]*>(.*?)(?:<div id="tab_|$)', resp.text, re.DOTALL)
    if tab:
        print(f"  tab_SupportStaffOpportunities content[:1000]: {tab.group(1)[:1000]!r}")
    else:
        print("  tab_SupportStaffOpportunities anchor not found in static HTML")
    iframe = re.findall(r'<iframe[^>]+src="([^"]+)"', resp.text)
    print(f"  iframes found: {iframe}")


def main() -> None:
    check_marshall_dennehey()
    check_wilson_sonsini()
    check_wilmerhale()
    check_ogletree_deakins()
    check_kramer_levin()
    check_duane_morris()


if __name__ == "__main__":
    main()
