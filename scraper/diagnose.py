"""Round 9 diagnostic: Wilson Elser -- inspect the React bundle for API hints.

Confirmed: the site is a bare React SPA (<div id="root"></div> +
/static/js/main.<hash>.js) served identically for every route. No
server-rendered HTML exists to scrape. Last automated attempt: fetch the
JS bundle itself and grep for an API base URL / endpoint pattern before
falling back to manual DevTools inspection (same as Reed Smith).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30


def main() -> None:
    page = requests.get("https://www.wilsonelser.com/careers", headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    js_paths = re.findall(r'src="(/static/js/main\.[^"]+\.js)"', page.text)
    print(f"JS bundle paths found: {js_paths}")
    if not js_paths:
        print("no main bundle found in HTML")
        return

    js_url = "https://www.wilsonelser.com" + js_paths[0]
    print(f"fetching {js_url} ...")
    js_resp = requests.get(js_url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    js_text = js_resp.text
    print(f"bundle size: {len(js_text)} chars")

    # Look for absolute API hosts, /api/ paths, graphql, or job-related endpoint strings.
    patterns = [
        r'https?://[a-zA-Z0-9.\-]+\.(?:icims|myworkdayjobs|greenhouse|lever|smartrecruiters|'
        r'applicantstack|clearcompany|hrmdirect|avature|oraclecloud|phenompeople)\.[a-z]+[^"\'\s]*',
        r'["\'](/api/[^"\']{0,80})["\']',
        r'["\']([^"\']{0,40}graphql[^"\']{0,40})["\']',
        r'["\']([^"\']{0,40}job[_-]?openings?[^"\']{0,40})["\']',
        r'["\']([^"\']{0,40}careers?[/_-][a-z]{2,40}[^"\']{0,40})["\']',
    ]
    found = set()
    for pat in patterns:
        for m in re.findall(pat, js_text, re.IGNORECASE):
            found.add(m if isinstance(m, str) else m[0])
    print(f"\ncandidate API/endpoint strings found ({len(found)}):")
    for s in sorted(found)[:40]:
        print(" ", s)


if __name__ == "__main__":
    main()
