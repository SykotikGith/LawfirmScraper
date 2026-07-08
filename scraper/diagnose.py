"""Diagnostic: deep-dive O'Melveny & Myers' viGlobal (viRecruit) page --
it's clearly the actual job application portal itself ("viDesktop", 1.3MB),
not a marketing shell, so the real job data must be somewhere in that
page: an embedded table, an inline JSON blob, or an API endpoint the page
calls. Look for all of those.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
URL = "https://ommcareers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx?Tag=84c08942-ea6c-4707-a535-258e400c6b3d"


def main() -> None:
    resp = requests.get(URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    print(f"status={resp.status_code} len={len(text)}")

    soup = BeautifulSoup(text, "lxml")

    tables = soup.find_all("table")
    print(f"\n<table> elements: {len(tables)}")
    for i, t in enumerate(tables[:5]):
        rows = t.find_all("tr")
        print(f"  table[{i}]: {len(rows)} rows, id={t.get('id')!r} class={t.get('class')!r}")

    grids = soup.select("[id*='grid' i], [class*='grid' i], [id*='job' i], [class*='job' i]")
    print(f"\nelements with 'grid' or 'job' in id/class: {len(grids)}")
    for el in grids[:15]:
        print(f"  <{el.name}> id={el.get('id')!r} class={el.get('class')!r} text={el.get_text(strip=True)[:60]!r}")

    # Inline JSON blobs (common in ASP.NET apps using a JS-side grid/datatable).
    json_like = re.findall(r'var\s+\w+\s*=\s*(\{.{0,200}|\[.{0,200})', text)
    print(f"\ninline var-assigned JSON-looking blobs (first 10 of {len(json_like)}):")
    for j in json_like[:10]:
        print(f"  {j!r}")

    # API/ajax endpoint references.
    api_like = sorted(set(re.findall(r'["\']([^"\']*(?:\.asmx|\.ashx|/api/|WebMethod|GetJobs|SearchJobs)[^"\']*)["\']', text, re.IGNORECASE)))
    print(f"\napi/handler-like strings (first 15 of {len(api_like)}):")
    for a in api_like[:15]:
        print(f"  {a}")

    # Same-origin script src references, in case data loads from a separate JS file.
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', text)
    same_origin = [s for s in scripts if "viglobalcloud.com" in s or s.startswith("/") or s.startswith("../")]
    print(f"\nsame-origin script srcs (first 15 of {len(same_origin)}):")
    for s in same_origin[:15]:
        print(f"  {s}")


if __name__ == "__main__":
    main()
