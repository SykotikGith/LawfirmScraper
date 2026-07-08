"""Round 7 diagnostic: Wilson Elser.

Config currently points at
https://www.wilsonelser.com/careers/professional_staff/current-opportunities
with link_selector "a[href*='/job_openings/']" -- a guess from research,
never live-verified. It returned 0 postings on the last two live runs.
Check whether the URL/path is even right, and if not, hunt for the real
listing page.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def main() -> None:
    print("=== Wilson Elser: current config URL ===")
    url = "https://www.wilsonelser.com/careers/professional_staff/current-opportunities"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    if resp.status_code == 200:
        text = resp.text
        print(f"'/job_openings/' occurrences: {text.count('/job_openings/')}")
        soup = BeautifulSoup(text, "lxml")
        links = [a.get("href", "") for a in soup.select("a[href]")]
        career_like = sorted(set(h for h in links if "career" in h.lower() or "job" in h.lower()))
        print(f"career/job-like hrefs found ({len(career_like)}):")
        for h in career_like[:25]:
            print(" ", h)

    print("\n=== Wilson Elser: base careers page ===")
    for path in [
        "/careers",
        "/careers-attorneys",
        "/careers-business-legal-professionals",
        "/careers/all_openings",
        "/careers/professional_staff",
    ]:
        u = f"https://www.wilsonelser.com{path}"
        try:
            r = requests.get(u, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
            print(f"{path}: status={r.status_code} final_url={r.url} len={len(r.text)}")
        except Exception as exc:  # noqa: BLE001
            print(f"{path}: EXCEPTION {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
