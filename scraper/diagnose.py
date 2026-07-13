"""Diagnostic: figure out why CustomHTMLAdapter returned 0 postings for
Reed Smith. config.py already flagged this as a risk -- careers.reedsmith.com
is a front-end search/results layer over an Oracle PeopleSoft HCM Recruiting
(Fluid Candidate Gateway) backend at recruit.reedsmith.com, and it was
unclear whether the front-end is server-rendered or JS-driven. This fetches
both the configured list_url and the PeopleSoft host directly, and prints
enough structural clues (script tags, framework markers, embedded JSON, any
API-looking path fragments) to tell what's actually there.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
LIST_URL = "https://careers.reedsmith.com/jobs/vacancy/find/results"
PEOPLESOFT_HOST = "https://recruit.reedsmith.com/"


def inspect(label: str, url: str) -> str:
    print(f"\n=== {label} -- {url} ===")
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return ""
    text = resp.text
    print(f"  final url after redirects: {resp.url}")
    print(f"  status={resp.status_code}  content-length={len(text)}")
    print(f"  'JobOpeningId' in page: {'JobOpeningId' in text}")
    print(f"  'HRS_CE' in page (PeopleSoft component marker): {'HRS_CE' in text}")
    print(f"  'ng-version' present (Angular): {'ng-version' in text}")
    print(f"  'data-reactroot' or React bundle hint present: {'data-reactroot' in text or 'react' in text.lower()}")
    print(f"  'ko.' knockout marker present: {'ko.applyBindings' in text or 'data-bind=' in text}")

    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    print(f"  <script src=...> tags found ({len(script_srcs)}):")
    for src in script_srcs[:15]:
        print(f"    {src}")

    api_hints = re.findall(
        r'["\'](/[\w./-]*(?:api|svc|search|vacancy|opening|posting)[\w./-]*)["\']', text, re.IGNORECASE
    )
    print(f"  possible API path fragments referenced in page: {sorted(set(api_hints))[:20]}")
    return text


def main() -> None:
    text = inspect("Reed Smith configured list_url", LIST_URL)
    inspect("Reed Smith PeopleSoft host root", PEOPLESOFT_HOST)

    if text:
        print("\n--- first 2500 chars of list_url HTML (for manual inspection) ---")
        print(text[:2500])


if __name__ == "__main__":
    main()
