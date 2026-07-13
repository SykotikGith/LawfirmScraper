"""Diagnostic round 2: Akerman's UltiPro board is a Knockout.js page
(data-bind="text: title()"), not the classic static-link template
UltiProAdapter originally assumed. Round 1 found real API path fragments
referenced in the page: JobBoardView/LoadSearchResults and
JobBoardView/GetOpportunityMatchCount. This probes those endpoints
directly (a few request-shape guesses each, since the exact expected body
isn't known yet) and prints surrounding JS context from the raw page so we
can see how the client actually calls them.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
BASE = "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/b855fc7e-c6e0-90cc-b829-ddbebeb6f274"


def print_context(text: str, needle: str, radius: int = 400) -> None:
    for m in re.finditer(re.escape(needle), text):
        start = max(0, m.start() - radius)
        end = min(len(text), m.end() + radius)
        print(f"\n--- context around {needle!r} @ offset {m.start()} ---")
        print(text[start:end])


def fetch_page() -> str:
    resp = requests.get(BASE + "/", headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    return resp.text


def show_js_context(text: str) -> None:
    print("\n\n=== JS context around the known endpoint names ===")
    print_context(text, "LoadSearchResults")
    print_context(text, "GetOpportunityMatchCount")
    print_context(text, "JobSearchAgent")

    print("\n\n=== searching for embedded pre-loaded data (ko.observableArray / opportunities) ===")
    print_context(text, "ko.observableArray", radius=200)
    for needle in ["opportunities", "Opportunities", "searchResults", "SearchResults"]:
        idx = text.find(needle)
        if idx != -1:
            print(f"\nfirst occurrence of {needle!r} at offset {idx}:")
            print(text[max(0, idx - 150):idx + 300])


def probe_endpoints() -> None:
    print("\n\n=== probing candidate API calls ===")
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json, text/plain, */*"

    attempts = [
        ("GET", f"{BASE}/JobBoardView/LoadSearchResults", None),
        ("POST", f"{BASE}/JobBoardView/LoadSearchResults", {}),
        ("POST", f"{BASE}/JobBoardView/LoadSearchResults", {"opportunitySearch": {"Text": "", "PageNumber": 1, "PageSize": 50}}),
        ("POST", f"{BASE}/JobBoardView/LoadSearchResults", {"Text": "", "PageNumber": 1, "PageSize": 50}),
        ("GET", f"{BASE}/JobBoardView/GetOpportunityMatchCount", None),
        ("POST", f"{BASE}/JobBoardView/GetOpportunityMatchCount", {}),
    ]

    for method, url, body in attempts:
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            else:
                resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
            snippet = resp.text[:500]
            print(f"\n{method} {url}  body={json.dumps(body)}")
            print(f"  status={resp.status_code}  len={len(resp.text)}")
            print(f"  body[:500]={snippet!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"\n{method} {url}  body={json.dumps(body)}")
            print(f"  EXCEPTION: {type(exc).__name__}: {exc}")


def main() -> None:
    text = fetch_page()
    show_js_context(text)
    probe_endpoints()


if __name__ == "__main__":
    main()
