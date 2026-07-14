"""Round 2 for the 3 remaining leads.

- Arnold & Porter: round 1 confirmed Coveo (static.cloud.coveo.com) --
  the exact same enterprise search layer already blocking Covington &
  Burling in this project. Coveo sites usually have a public search API
  once you have an access token/organization ID -- this looks for those
  in the page's own embedded config before concluding it's blocked the
  same way.
- Dechert: round 1 found nothing (0 job-related class/id hits, no /api/
  paths) despite a real 80KB response -- this searches the full page
  text more broadly (not just class/id attributes) for any job-title-
  shaped content, and checks for an iframe or AEM content-fragment
  reference that might hold the real listing.
- Akin Gump: round 1's jobid= link search came up empty even though the
  page is a real SilkRoad form (unlike WilmerHale, where jobid= links
  were directly embedded). This tries the same app.jobsearch fuseaction
  trick that worked for WilmerHale, adapted to Akin Gump's URL shape.

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


def check_arnold_porter() -> None:
    section("Arnold & Porter -- hunting for embedded Coveo config (org id / access token)")
    url = "https://www.arnoldporter.com/en/careers/professional-staff/current-opportunities?skip=0&reload=false&scroll=0"
    resp = fetch(url)
    if resp is None:
        return
    org_hints = re.findall(r'"?organizationId"?\s*[:=]\s*[\'"]([^\'"]+)[\'"]', resp.text)
    token_hints = re.findall(r'"?accessToken"?\s*[:=]\s*[\'"]([^\'"]{10,80})[\'"]', resp.text)
    print(f"  organizationId references: {org_hints}")
    print(f"  accessToken references (may be truncated): {token_hints}")
    coveo_hints = re.findall(r'coveo[.\w]*\s*[:=]\s*[\'"]([^\'"]+)[\'"]', resp.text, re.I)
    print(f"  other coveo.* config assignments: {coveo_hints[:10]}")


def check_dechert() -> None:
    section("Dechert -- full-page hunt for job content / iframe / AEM content fragment")
    resp = fetch("https://www.dechert.com/careers.html")
    if resp is None:
        return
    iframe = re.findall(r'<iframe[^>]+src="([^"]+)"', resp.text)
    print(f"  iframes found: {iframe}")
    data_src = re.findall(r'data-(?:src|url|endpoint|component-path)="([^"]+)"', resp.text)
    print(f"  data-src/url/endpoint/component-path attrs: {sorted(set(data_src))[:15]}")
    position_mentions = re.findall(r'.{40}Business\s+Professional.{40}', resp.text)
    print(f"  'Business Professional' context snippets: {position_mentions[:5]}")


def check_akin_gump() -> None:
    section("Akin Gump -- trying app.jobsearch fuseaction (worked for WilmerHale)")
    for url in [
        "https://jobs.silkroad.com/AkinGump/AkinGump?fuseaction=app.jobsearch",
        "https://jobs.silkroad.com/AkinGump/AkinGump/JobSearch",
        "https://jobs.silkroad.com/AkinGump/AkinGump?fuseaction=app.joblist",
    ]:
        resp = fetch(url)
        if resp is None:
            print(f"  {url} -> EXCEPTION (see above)")
            continue
        print(f"  {url} -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            job_links = re.findall(r'<a[^>]+href="([^"]*jobid=\d+[^"]*)"[^>]*>([^<]+)</a>', resp.text, re.I)
            print(f"    jobid= links found: {len(job_links)}")
            for href, text in job_links[:10]:
                print(f"      {text.strip()!r} -> {href}")


def main() -> None:
    check_arnold_porter()
    check_dechert()
    check_akin_gump()


if __name__ == "__main__":
    main()
