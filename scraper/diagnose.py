"""Diagnostic round 3 for Reed Smith: found the real mechanism -- this
PageUp/eArcu page loads its results grid via an AJAX call after page load:
/jobs/vacancy/find/results/ajaxaction/posbrowser_gridhandler/?pagestamp=<token>
extracted directly from an inline <script> on the list page. This fetches
the list page first (to get a live pagestamp token and matching session
cookies, same priming pattern as WorkdayAdapter), then hits that ajaxaction
URL and prints what comes back -- HTML fragment or JSON, and whether it
actually contains job listings.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
LIST_URL = "https://careers.reedsmith.com/jobs/vacancy/find/results"

PAGESTAMP_RE = re.compile(r"ajaxaction/posbrowser_gridhandler/\?pagestamp=([\w-]+)")


def main() -> None:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    resp = session.get(LIST_URL, timeout=TIMEOUT)
    text = resp.text
    print(f"list page: status={resp.status_code} len={len(text)}")
    print(f"cookies set: {list(session.cookies.keys())}")

    match = PAGESTAMP_RE.search(text)
    if not match:
        print("Could not find a pagestamp token in the page -- printing all ajaxaction occurrences:")
        for m in re.finditer(r"ajaxaction[^\s'\"]*", text):
            print(f"  {m.group(0)}")
        return

    pagestamp = match.group(1)
    print(f"\nfound pagestamp: {pagestamp}")

    ajax_url = f"{LIST_URL}/ajaxaction/posbrowser_gridhandler/?pagestamp={pagestamp}"
    ajax_headers = dict(DEFAULT_HEADERS)
    ajax_headers["X-Requested-With"] = "XMLHttpRequest"
    ajax_headers["Referer"] = LIST_URL

    ajax_resp = session.get(ajax_url, headers=ajax_headers, timeout=TIMEOUT)
    print(f"\najax GET {ajax_url}")
    print(f"status={ajax_resp.status_code}  content-type={ajax_resp.headers.get('Content-Type')}  len={len(ajax_resp.text)}")

    body = ajax_resp.text
    print(f"\nlooks like JSON: {body.strip().startswith('{') or body.strip().startswith('[')}")
    print(f"'href' count in response: {body.count('href')}")
    print(f"'vacancy' count in response: {body.lower().count('vacancy')}")

    print("\n--- first 3000 chars of ajax response ---")
    print(body[:3000])


if __name__ == "__main__":
    main()
