"""Diagnostic: figure out why UltiProAdapter returned 0 postings for Akerman.

UltiProAdapter assumed the classic server-rendered UltiPro JobBoard template
(plain <a href="OpportunityDetail.aspx?opportunityId=...">Title</a> links in
static HTML). It returned 0 postings for Akerman, which means that
assumption is wrong -- either it's the newer Angular JobBoard template
(client-side JS, nothing in static HTML), or the same classic template but
with different markup than expected. This fetches the raw page and prints
enough structural clues to tell which, without dumping the whole HTML blob.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
AKERMAN_URL = "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/b855fc7e-c6e0-90cc-b829-ddbebeb6f274/"


def check_akerman() -> None:
    print(f"=== Akerman (UltiPro) -- {AKERMAN_URL} ===")
    resp = requests.get(AKERMAN_URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    print(f"status={resp.status_code}  content-length={len(text)}")

    print(f"\n'OpportunityDetail.aspx' in page: {'OpportunityDetail.aspx' in text}")
    print(f"'opportunityId' in page (any case): {'opportunityid' in text.lower()}")
    print(f"'ng-version' attribute present (Angular marker): {'ng-version' in text}")
    print(f"'ng-app' attribute present (AngularJS marker): {'ng-app' in text}")

    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    print(f"\n<script src=...> tags found ({len(script_srcs)}):")
    for src in script_srcs[:20]:
        print(f"  {src}")

    json_scripts = re.findall(
        r'<script[^>]*type=["\']application/json["\'][^>]*id=["\']([^"\']*)["\']', text
    )
    print(f"\n<script type=\"application/json\"> blocks found: {json_scripts}")

    window_assigns = re.findall(r"window\.(\w+)\s*=", text)
    print(f"window.X = ... assignments found: {sorted(set(window_assigns))}")

    # Common REST-ish path fragments that might hint at the real API, if any
    # are referenced directly in the page's inline script/markup.
    api_hints = re.findall(r'["\'](/[\w./-]*(?:api|svc|search|opportunit)[\w./-]*)["\']', text, re.IGNORECASE)
    print(f"\nPossible API path fragments referenced in page: {sorted(set(api_hints))[:20]}")

    print("\n--- first 3000 chars of raw HTML (for manual inspection if the above is inconclusive) ---")
    print(text[:3000])


def main() -> None:
    check_akerman()


if __name__ == "__main__":
    main()
