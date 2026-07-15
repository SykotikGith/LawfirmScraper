"""Category 2, round 3 -- following through on both breakthroughs.

- Kirkland & Ellis: round 2 confirmed the site is a Talemetry Career
  Sites product (Cornerstone) gated by Cloudflare's JS bot-management
  challenge (cdn-cgi/challenge-platform scripts), which a genuine
  headless-Chromium session passes -- but the bare /jobs/search/ page
  only rendered facet filter counts, no individual job rows (probably
  because no location/category filter is selected by default). This
  navigates to one of the real facet links found in round 2
  (/search/jobs/in/chicago, Chicago shows 39 openings) to find the
  actual per-job row markup.
- McDermott: round 2's click on "SEE OPEN ROLES" kept failing because
  a OneTrust cookie-consent overlay intercepted every click attempt.
  The link's real href was captured in the failed locator's debug info
  though (/careers/open-roles/) -- this navigates straight there
  instead of clicking, sidestepping the consent banner entirely.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
WAIT_MS = 5_000


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
            section("Kirkland & Ellis -- Chicago-filtered results page")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/search/jobs/in/chicago", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            for sel in [
                "li.job", "tr.job", "div.job", "article",
                "[class*='job-result']", "[class*='jobresult']",
                "[class*='search-result']", "[class*='job-list']",
                "a[href*='/job/']", "a[href*='/jobs/']",
            ]:
                els = page.query_selector_all(sel)
                if els:
                    print(f"  selector {sel!r}: {len(els)} elements")

            body_html = page.content()
            idx = body_html.find("job-results")
            if idx == -1:
                idx = body_html.find("search-results")
            print(f"  HTML near results container[:4000]: {body_html[idx:idx+4000]!r}")

            body_text = page.inner_text("body")
            print(f"  body text[:2500]: {body_text[:2500]!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- navigating straight to /careers/open-roles/")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            candidates = []

            def on_resp(r):
                ct = r.headers.get("content-type", "")
                if "json" in ct.lower() or re.search(r"job|career|search|api", r.url, re.I):
                    if not any(n in r.url.lower() for n in ["gtm.js", "analytics", ".woff", ".css", ".png", ".jpg", ".svg", "cookielaw", "onetrust"]):
                        candidates.append((r.url, r.status, ct))

            page.on("response", on_resp)
            page.goto("https://www.mcdermottlaw.com/careers/open-roles/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  current URL: {page.url}")
            print(f"  title: {page.title()!r}")
            print("  network responses matching job/career/search/api:")
            for url, status, ct in candidates[:20]:
                print(f"    [{status}] {ct} {url}")
            body = page.inner_text("body")
            print(f"  body text[:2000]: {body[:2000]!r}")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
