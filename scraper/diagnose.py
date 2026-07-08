"""Diagnostic: investigate 4 new leads.

- Blank Rome and Covington & Burling: both already confirmed as real
  Workday tenants (via ats_probe.py's path-specific-error signal) but
  missing their site slug. Check the specific business-professionals
  careers URLs found manually for an embedded myworkdayjobs.com link.
- O'Melveny & Myers: the URL found is viglobalcloud.com
  (viGlobal/viRecruit), a legal-industry-specific ATS not seen anywhere
  else in this project -- like Debevoise's Circa Works surprise, this
  means the "omm" Workday tenant ats_probe.py found is likely a
  dormant/internal tenant, not the real external recruiting system.
  Inspect the page's raw structure to figure out how to scrape it.
- Locke Lord / Troutman Pepper Locke: Locke Lord merged into Troutman
  Pepper Locke on Jan 1, 2025. "Troutman Pepper Locke" is a SEPARATE
  entry in ats_probe.py's original 69-firm list (slug
  "troutmanpepperlocke"/"troutman") that came back "needs manual check"
  in the last full run, while "Locke Lord" (slug "lockelord") was
  separately confirmed as a real Workday tenant. Check whether the
  merged firm's real careers page (troutman.com or similar) embeds a
  Workday link, and whether it points at the same lockelord tenant or
  something else entirely.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20
WORKDAY_URL_RE = re.compile(
    r"https?://([a-zA-Z0-9\-]+)\.(wd\d+)\.myworkdayjobs\.com/([a-zA-Z0-9_\-]+)"
)


def sniff_page(label: str, url: str) -> None:
    print(f"\n{label}: {url}")
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION {type(exc).__name__}: {exc}")
        return
    print(f"  status={resp.status_code} len={len(resp.text)} content-type={resp.headers.get('content-type')}")
    text = resp.text
    match = WORKDAY_URL_RE.search(text)
    if match:
        tenant, pod, site = match.groups()
        print(f"  FOUND WORKDAY LINK: tenant={tenant} pod={pod} site={site}")
    else:
        print("  no myworkdayjobs.com link found")
    print(f"  body[:500]: {text[:500]!r}")


def main() -> None:
    sniff_page("Blank Rome", "https://www.blankrome.com/careers/overview/business-professionals/")
    sniff_page("Covington & Burling", "https://www.cov.com/en/careers/business-professionals/employment-opportunities")
    sniff_page(
        "O'Melveny & Myers (viGlobal)",
        "https://ommcareers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx"
        "?Tag=84c08942-ea6c-4707-a535-258e400c6b3d",
    )
    for path in ["", "/careers", "/en/careers", "/en-us/careers"]:
        sniff_page("Troutman Pepper Locke", f"https://www.troutman.com{path}")


if __name__ == "__main__":
    main()
