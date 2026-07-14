"""Round 3 for the 4 firms round 2 confirmed real data exists for, but
without quite enough detail to build an adapter yet:

- Wilson Sonsini: FacetWP results confirmed real (round 2), but the
  generic a[href*='/openings/'] selector would double-count each posting
  (a title link AND a separate "Details" link share the same href) --
  this dumps the raw HTML around one result card to find a selector that
  only matches the title link.
- WilmerHale: fuseaction=app.jobsearch returned a much bigger response
  (60KB vs ~3.7KB for the other guesses) -- almost certainly real
  results this time. Dumping enough of it to find real job titles/links.
- Ogletree Deakins: found a genuine working JSON API
  (careers.ogletree.com/api/jobs) in round 2 -- this pulls the full
  schema of one record plus checks for a pagination parameter.
- Kramer Levin (HSF Kramer): confirmed real Phenom job-card CSS classes
  in round 2, but they were unrendered template placeholders (e.g.
  "phs-${category.total_count}") -- data loads via a separate API call.
  Trying a few common Phenom endpoint conventions.

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


def check_wilson_sonsini() -> None:
    section("Wilson Sonsini -- raw HTML around one result card")
    resp = fetch("https://careers.wsgr.com/openings/?_opening_type=82")
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    template = soup.select_one(".facetwp-template")
    if template is None:
        print("  .facetwp-template not found")
        return
    first_link = template.find("a", href=True)
    if first_link is None:
        print("  no <a> found inside .facetwp-template")
        return
    card = first_link.find_parent(["article", "li", "div"])
    print(f"  card tag/classes: <{card.name} class={card.get('class')}>" if card else "  no parent card found")
    print(f"  raw HTML around first card:\n{str(card)[:1500] if card else str(first_link)[:1500]}")


def check_wilmerhale() -> None:
    section("WilmerHale -- dumping app.jobsearch response")
    url = "https://wilmerhale-openhire.silkroad.com/epostings/index.cfm?fuseaction=app.jobsearch&company_id=16437&version=2"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    job_links = re.findall(r'<a[^>]+href="([^"]*jobid=\d+[^"]*)"[^>]*>([^<]+)</a>', resp.text, re.I)
    print(f"  jobid= links found: {len(job_links)}")
    for href, text in job_links[:15]:
        print(f"    {text.strip()!r} -> {href}")
    if not job_links:
        print(f"  body[:1500]: {resp.text[:1500]!r}")


def check_ogletree_deakins() -> None:
    section("Ogletree Deakins -- full schema + pagination check")
    resp = fetch("https://careers.ogletree.com/api/jobs")
    if resp is None:
        return
    data = resp.json()
    jobs = data.get("jobs", [])
    print(f"  jobs returned: {len(jobs)}")
    print(f"  top-level response keys: {list(data.keys())}")
    if jobs:
        print("  full schema of first job's 'data':")
        print(json.dumps(jobs[0].get("data", {}), indent=2)[:1500])
    print("\n  all titles:")
    for job in jobs:
        print(f"    - {job.get('data', {}).get('title')!r}")


def check_kramer_levin() -> None:
    section("Kramer Levin (HSF Kramer) -- probing common Phenom API endpoints")
    candidates = [
        "https://careers.hsfkramer.com/widgets/careersearch/search",
        "https://careers.hsfkramer.com/api/apply/v2/jobs?domain=careers.hsfkramer.com&start=0&num=20",
        "https://careers.hsfkramer.com/search-jobs/results",
        "https://careers.hsfkramer.com/global/en/us/search-results/getdata",
    ]
    for url in candidates:
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url} -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:300]: {resp.text[:300]!r}")

    # Also check for a JSON config blob embedded in the page itself (Phenom sites
    # sometimes embed the search API base URL in a window.PH_CONFIG-style script).
    resp = fetch("https://careers.hsfkramer.com/global/en/us/search-results")
    if resp:
        config_hints = re.findall(r'(PH_\w+|phApp\.\w+)\s*=\s*({[^;]{0,200}|"[^"]{0,200}")', resp.text)
        print(f"  PH_/phApp. config assignments found: {len(config_hints)}")
        for k, v in config_hints[:10]:
            print(f"    {k} = {v[:150]}")


def main() -> None:
    check_wilson_sonsini()
    check_wilmerhale()
    check_ogletree_deakins()
    check_kramer_levin()


if __name__ == "__main__":
    main()
