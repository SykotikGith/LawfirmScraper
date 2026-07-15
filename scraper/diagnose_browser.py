"""Round 6 -- last 3 firms (Ropes & Gray confirmed Cloudflare-blocked in round 5,
moved to MANUAL_CHECK_FIRMS, done).

- Paul Weiss: round 5 found the real row1 <tr> and confirmed the title
  ("Business Services Assistant") via a[id*='reqTitleLinkAction'], but the
  outerHTML dump got truncated before showing location/date. This grabs
  row.inner_text() instead (clean visible text, no HTML noise) for row1,
  and also counts how many rowN links exist so an adapter knows how to
  loop.
- Duane Morris: round 5 confirmed the careers page has a list of city
  names (Atlanta, Austin, Boca Raton, ...) as the "Current Opportunities"
  links, not actual job postings. This dumps each city link's href to see
  where they actually point -- likely a different ATS/portal per office,
  or a shared one with a location filter param.
- Crowell & Moring: round 5's regex-based href extraction failed against
  the real corrupted string for reasons still unclear (worked in isolated
  testing, not against the live page). Since we already know the intended
  destination from the raw href text itself
  (https://www.crowell.com/en/careers/professional-staff/open-positions),
  this skips parsing the broken link entirely and just navigates straight
  there to see whether that destination page is plain scrapable HTML.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
WAIT_MS = 4_000


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def run_safely(label: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - diagnostic script, one bad firm shouldn't kill the rest
        print(f"  EXCEPTION in {label}: {type(exc).__name__}: {exc}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def paul_weiss():
            section("Paul Weiss -- row inner_text + row count")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            try:
                page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
            except Exception as exc:
                print(f"  could not click Search: {exc}")
            page.wait_for_timeout(WAIT_MS)

            title_links = page.query_selector_all("a[id*='reqTitleLinkAction']")
            print(f"  total title links found: {len(title_links)}")
            for link in title_links:
                print(f"    id={link.get_attribute('id')!r} text={link.inner_text()!r}")

            row1 = page.query_selector("a[id='requisitionListInterface.reqTitleLinkAction.row1']")
            if row1:
                row = row1.evaluate_handle("el => el.closest('tr')")
                row_text = row.evaluate("el => el ? el.innerText : null")
                print(f"  row1 inner_text: {row_text!r}")
            ctx.close()

        def duane_morris():
            section("Duane Morris -- city link hrefs under Support Staff Opportunities")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto(
                "https://www.duanemorris.com/site/careers.html#SupportStaffOpportunities",
                wait_until="load",
            )
            page.wait_for_timeout(WAIT_MS)
            cities = [
                "Multiple Locations", "Atlanta", "Austin", "Boca Raton", "Boston",
                "Chicago", "Dallas", "Fort Worth", "Houston", "Los Angeles",
                "New York", "North Jersey", "Philadelphia", "Pittsburgh",
                "San Diego", "San Francisco", "Silicon Valley", "Washington D.C.",
            ]
            for city in cities:
                try:
                    link = page.get_by_role("link", name=city, exact=True).first
                    href = link.get_attribute("href", timeout=3000)
                    print(f"    {city}: {href!r}")
                except Exception as exc:
                    print(f"    {city}: EXCEPTION {type(exc).__name__}: {exc}")
            ctx.close()

        def crowell_moring():
            section("Crowell & Moring -- navigating straight to the known open-positions URL")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            candidates = []

            def on_resp(r):
                ct = r.headers.get("content-type", "")
                if "json" in ct.lower() or re.search(r"job|career|search|api", r.url, re.I):
                    if not any(n in r.url.lower() for n in ["gtm.js", "analytics", ".woff", ".css", ".png", ".jpg", ".svg", "cookielaw", "onetrust"]):
                        candidates.append((r.url, r.status, ct))

            page.on("response", on_resp)
            page.goto(
                "https://www.crowell.com/en/careers/professional-staff/open-positions",
                wait_until="load",
            )
            page.wait_for_timeout(WAIT_MS)
            print(f"  page title: {page.title()!r}")
            print(f"  final URL: {page.url}")
            for url, status, ct in candidates[:20]:
                print(f"    [{status}] {ct} {url}")
            print(f"  body text[:2000]: {page.inner_text('body')[:2000]!r}")
            ctx.close()

        run_safely("Paul Weiss", paul_weiss)
        run_safely("Duane Morris", duane_morris)
        run_safely("Crowell & Moring", crowell_moring)

        browser.close()


if __name__ == "__main__":
    main()
