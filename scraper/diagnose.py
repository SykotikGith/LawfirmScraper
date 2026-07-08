"""Diagnostic: do ApplicantStack, HRMdirect, or Greenhouse have the same
wildcard/shared-edge false-positive problem just found in Workday (fixed)
and iCIMS (unfixable, dropped from ats_probe.py)?

Tests known-real tenants confirmed elsewhere in this project (Hinshaw on
ApplicantStack, Fisher Phillips on HRMdirect, Wilson Elser on Greenhouse)
against definitely-fake slugs on the same three patterns ats_probe.py
still relies on. If a fake slug returns the same non-404 status as the
real tenant, that pattern needs the same treatment as Workday/iCIMS
before any of its "hits" in ats_probe.py's results can be trusted.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15
FAKE_SLUGS = ["thisisnotarealfirmxyz123", "totallymadeupslugabc999"]


def check(label: str, url: str) -> None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        print(f"  [{label}] {url}\n    status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    except requests.exceptions.RequestException as exc:
        print(f"  [{label}] {url}\n    EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== ApplicantStack (known-real: hinshawlaw) ===")
    check("real", "https://hinshawlaw.applicantstack.com/")
    for slug in FAKE_SLUGS:
        check("fake", f"https://{slug}.applicantstack.com/")

    print("\n=== HRMdirect (known-real: fisherphillips) ===")
    check("real", "https://fisherphillips.hrmdirect.com/")
    for slug in FAKE_SLUGS:
        check("fake", f"https://{slug}.hrmdirect.com/")

    print("\n=== Greenhouse (known-real: wilsonelser) ===")
    check("real", "https://job-boards.greenhouse.io/wilsonelser")
    for slug in FAKE_SLUGS:
        check("fake", f"https://job-boards.greenhouse.io/{slug}")


if __name__ == "__main__":
    main()
