"""Round 8 diagnostic: Wilson Elser.

Every path tried in round 7 returned the identical 1460-byte response
regardless of validity -- that's not real page content, print the whole
thing to see what's actually being served (JS shell? bot challenge?
misconfigured redirect?).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def main() -> None:
    url = "https://www.wilsonelser.com/careers"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"status={resp.status_code} final_url={resp.url}")
    print(f"headers: {dict(resp.headers)}")
    print(f"\nfull body ({len(resp.text)} chars):")
    print(resp.text)


if __name__ == "__main__":
    main()
