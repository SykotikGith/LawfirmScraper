"""Category 2, round 2 -- the two real breakthroughs from round 1.

Round 1 confirmed the 9 iCIMS AWS WAF tenants (Orrick, Milbank, Lewis
Brisbois, Gordon Rees, Foley & Lardner, Nelson Mullins, Mayer Brown,
Latham & Watkins, Willkie Farr) are STILL blocked (405, "Human
Verification" challenge) even with a genuine headless-Chromium session
-- config.py's MANUAL_CHECK_FIRMS entries for all 9 have already been
updated to reflect that confirmed-with-a-real-browser finding, nothing
more to try there per the "don't force it" instruction.

But two firms broke through:
- Kirkland & Ellis: staffjobsus.kirkland.com/jobs/search/ rendered a
  full real job board (200, real category/location facet counts) with
  a genuine headless browser -- the Cloudflare challenge that blocks
  plain HTTP didn't trigger this time. This finds the actual per-job
  row markup so an adapter can be built.
- McDermott Will & Emery: mcdermottlaw.com/careers rendered the real
  marketing homepage (200) past the Imperva block that blocks plain
  HTTP -- but that's just the homepage, not the job listing itself.
  This clicks through "SEE OPEN ROLES" to find the actual listing page
  and checks whether IT also renders past the block, or hits a second
  challenge layer.

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
            section("Kirkland & Ellis -- finding real job-row markup")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            candidates = []

            def on_resp(r):
                ct = r.headers.get("content-type", "")
                if "json" in ct.lower() or re.search(r"job|search|api", r.url, re.I):
                    if not any(n in r.url.lower() for n in ["gtm.js", "analytics", ".woff", ".css", ".png", ".jpg", ".svg", "cookielaw", "onetrust"]):
                        candidates.append((r.url, r.status, ct))

            page.on("response", on_resp)
            page.goto("https://staffjobsus.kirkland.com/jobs/search/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            print("  network responses matching job/search/api:")
            for url, status, ct in candidates[:20]:
                print(f"    [{status}] {ct} {url}")

            # Look for common ATS job-row containers.
            for sel in ["li.job", "tr.job", "div.job", "[class*='job-result']", "[class*='jobresult']", "article"]:
                els = page.query_selector_all(sel)
                if els:
                    print(f"  selector {sel!r}: {len(els)} elements")

            # Dump a broad region of the results area for manual inspection.
            body_html = page.content()
            idx = body_html.find("Filter Results")
            print(f"  HTML near 'Filter Results'[:4000]: {body_html[idx:idx+4000]!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- clicking through to the real job listing")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://www.mcdermottlaw.com/careers", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            try:
                page.get_by_text("SEE OPEN ROLES", exact=False).first.click(timeout=5000)
                page.wait_for_timeout(WAIT_MS)
                print("  clicked 'SEE OPEN ROLES'")
            except Exception as exc:
                print(f"  could not click SEE OPEN ROLES: {exc}")
            print(f"  current URL: {page.url}")
            print(f"  title: {page.title()!r}")
            body = page.inner_text("body")
            print(f"  body text[:1500]: {body[:1500]!r}")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
