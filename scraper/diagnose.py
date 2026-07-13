"""Diagnostic round 2 for Reed Smith: the original config.py assumption
(Oracle PeopleSoft at recruit.reedsmith.com) was wrong -- that host doesn't
even resolve. Round 1 found this is actually PageUp/eArcu (meta
name="author" content="PageUp Europe", earcu-details meta tag, Astro+Vue
components under /jobs/custom/ReedSmith_02/), a platform not seen anywhere
else in this project. Round 1 only printed the <head> -- this looks at the
<body> content (where job listings would actually render) and searches for
any embedded JSON/API hints specific to PageUp/eArcu's search results.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
LIST_URL = "https://careers.reedsmith.com/jobs/vacancy/find/results"


def main() -> None:
    resp = requests.get(LIST_URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    print(f"status={resp.status_code}  content-length={len(text)}")

    body_start = text.find("<body")
    print(f"\n<body> starts at offset {body_start}")

    print("\n=== searching for vacancy/job listing markup ===")
    for needle in ["vacancy", "Vacancy", "job-item", "job-card", "js-vacancy", "data-vacancy", "results-list", "no results", "No results", "No jobs"]:
        count = text.count(needle)
        if count:
            idx = text.find(needle)
            print(f"\n'{needle}' occurs {count}x, first at offset {idx}:")
            print(text[max(0, idx - 200):idx + 400])

    print("\n\n=== <div>/<section> ids and classes containing 'result' or 'list' ===")
    containers = re.findall(r'<(?:div|section|ul)[^>]+(?:id|class)=["\']([^"\']*(?:result|list|search)[^"\']*)["\'][^>]*>', text, re.IGNORECASE)
    for c in sorted(set(containers))[:30]:
        print(f"  {c!r}")

    print("\n\n=== any inline <script> (not src=) containing 'vacanc' or 'job' data ===")
    inline_scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.DOTALL | re.IGNORECASE)
    print(f"inline <script> blocks found: {len(inline_scripts)}")
    for script in inline_scripts:
        if re.search(r"vacanc|job", script, re.IGNORECASE):
            print("\n--- inline script snippet (first 800 chars) ---")
            print(script[:800])

    print("\n\n=== raw body content, offset body_start to body_start+4000 ===")
    if body_start != -1:
        print(text[body_start:body_start + 4000])


if __name__ == "__main__":
    main()
