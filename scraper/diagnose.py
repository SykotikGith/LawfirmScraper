"""Diagnostic: re-check Blank Rome and Covington & Burling for BOTH known
Workday URL formats -- the earlier scans only regexed for the old
{tenant}.{pod}.myworkdayjobs.com pattern and missed the newer shared
wd{N}.myworkdaysite.com/recruiting/{tenant}/{site} format White & Case
just revealed. That's the likely reason these two came back empty twice
in a row despite being confirmed real Workday tenants.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

OLD_FORMAT_RE = re.compile(
    r"https?://([a-zA-Z0-9\-]+)\.(wd\d+)\.myworkdayjobs\.com/([a-zA-Z0-9_\-]+)"
)
NEW_FORMAT_RE = re.compile(
    r"https?://(wd\d+)\.myworkdaysite\.com/recruiting/([a-zA-Z0-9\-]+)/([a-zA-Z0-9_\-]+)"
)


def sniff_page(label: str, url: str) -> None:
    print(f"\n{label}: {url}")
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION {type(exc).__name__}: {exc}")
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    text = resp.text

    old_matches = OLD_FORMAT_RE.findall(text)
    new_matches = NEW_FORMAT_RE.findall(text)
    if old_matches:
        print(f"  OLD-format Workday links found: {old_matches}")
    if new_matches:
        print(f"  NEW-format (myworkdaysite.com) Workday links found: {new_matches}")
    if not old_matches and not new_matches:
        print("  still no Workday link of either format found")
        # Also check generically for "workday" as a substring anywhere, in
        # case it's referenced without a full URL (e.g. in a data attribute
        # or a relative/obfuscated link).
        idx = text.lower().find("workday")
        if idx != -1:
            print(f"  but the word 'workday' DOES appear at index {idx}: "
                  f"{text[max(0, idx-150):idx+150]!r}")
        else:
            print("  and the word 'workday' does not appear anywhere in the page at all")


def main() -> None:
    sniff_page("Blank Rome", "https://www.blankrome.com/careers/overview/business-professionals/")
    sniff_page(
        "Covington & Burling",
        "https://www.cov.com/en/careers/business-professionals/employment-opportunities",
    )


if __name__ == "__main__":
    main()
