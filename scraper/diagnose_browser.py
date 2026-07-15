"""Category 2, round 7 -- final verification before building both adapters.

- Kirkland & Ellis: round 6 found real per-job links
  (staffjobsus.kirkland.com/jobs/<id>-<slug>) and confirmed
  /search/jobs/in/<city> URLs render real rows. Round 1 hit
  /jobs/search/ (WITH a trailing slash, unlike the no-trailing-slash
  version that hit the hard Cloudflare challenge in round 4) and got a
  clean 200 with facet content -- this checks whether THAT exact URL
  also renders individual job rows for ALL locations at once (no
  location selected), which would mean the adapter needs one page load
  instead of looping over ~13 city facets.
- McDermott: round 6 found the real Algolia multi-query endpoint
  (/1/indexes/*/queries) returns real hits with post_title/permalink/
  taxonomies, but the sample hit got cut off at 800 chars before a
  location field (if any) was visible. This dumps 2 full hit objects
  untruncated to find the location field and confirm every field an
  adapter needs (title, location, url, id, description) is present.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
WAIT_MS = 6_000


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def run_safely(label: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        print(f"  EXCEPTION in {label}: {type(exc).__name__}: {exc}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def kirkland():
            section("Kirkland & Ellis -- does /jobs/search/ (trailing slash) show ALL jobs unfiltered?")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/jobs/search/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  status via title check: {page.title()!r}")
            job_links = page.query_selector_all("a[href*='staffjobsus.kirkland.com/jobs/']")
            print(f"  real job detail links found: {len(job_links)}")
            body = page.inner_text("body")
            idx = body.find("Jobs Found")
            print(f"  near 'Jobs Found': {body[max(0,idx-80):idx+80]!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- full untruncated hit objects")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            captured = []

            def on_resp(r):
                if "algolia" in r.url.lower() and "queries" in r.url.lower():
                    try:
                        resp_json = r.json() if r.ok else None
                    except Exception:
                        resp_json = None
                    if resp_json:
                        captured.append(resp_json)

            page.on("response", on_resp)
            page.goto("https://www.mcdermottlaw.com/careers/open-roles/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            for resp_json in captured:
                hits = resp_json.get("results", [{}])[0].get("hits", [])
                print(f"  hit count: {len(hits)}")
                for hit in hits[:2]:
                    print(f"  --- full hit ---")
                    print(json.dumps(hit, indent=2, default=str)[:3000])
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
