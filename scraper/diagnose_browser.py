"""Round 5 -- last 4 firms. Each section is now wrapped so one firm's
failure can't kill the rest of the run (round 4 lost the entire Ropes &
Gray section because Crowell & Moring's URL handling threw an unhandled
exception partway through).

- Paul Weiss: round 4 confirmed the real per-row id pattern
  (requisitionListInterface.reqTitleLinkAction.rowN) and "11 jobs found"
  -- this finds the actual <tr> wrapping one full row (title + location +
  date) rather than the header/controls elements caught by the broader
  [id*='requisitionList'] search.
- Duane Morris: round 4 found real hrefs for Support Staff Opportunities
  and Lateral Current Opportunities (both same-page hash fragments) --
  clicking them didn't reveal new content in earlier rounds because the
  fragment differs by capitalization from what was tried; retrying with
  the exact href found.
- Crowell & Moring: the corrupted href actually does contain a real URL
  in parentheses (confirmed working in isolation) -- this retries the
  extraction with a fallback (just look for any https:// substring) and
  proper exception handling so a bad URL can't crash the run.
- Ropes & Gray: never got to run last round -- retrying the "US Careers"
  click-through now.

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
            section("Paul Weiss -- finding the full per-row markup")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            try:
                page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
            except Exception as exc:
                print(f"  could not click Search: {exc}")
            page.wait_for_timeout(WAIT_MS)
            title_link = page.query_selector("a[id='requisitionListInterface.reqTitleLinkAction.row1']")
            if title_link:
                row = title_link.evaluate_handle("el => el.closest('tr')")
                row_html = row.evaluate("el => el ? el.outerHTML : null")
                print(f"  row1 <tr> outerHTML[:2500]: {row_html[:2500] if row_html else None!r}")
            else:
                print("  row1 title link not found this time")
            ctx.close()

        def duane_morris():
            section("Duane Morris -- clicking the real Support Staff Opportunities href")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto(
                "https://www.duanemorris.com/site/careers.html#SupportStaffOpportunities",
                wait_until="load",
            )
            page.wait_for_timeout(WAIT_MS)
            body_text = page.inner_text("body")
            idx = body_text.find("Support Staff Opportunities")
            print(f"  text around 'Support Staff Opportunities'[{idx}:{idx+2000}]:")
            print(body_text[idx:idx + 2000])
            ctx.close()

        def crowell_moring():
            section("Crowell & Moring -- extracting and following the real Open Positions URL")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://www.crowell.com/en/careers/professional-staff", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            link = page.get_by_text("Open Positions", exact=False).first
            raw_href = link.get_attribute("href")
            print(f"  raw href: {raw_href!r}")
            urls_found = re.findall(r"https?://[^\s()\[\]]+", raw_href or "")
            print(f"  https:// substrings found: {urls_found}")
            if urls_found:
                real_url = urls_found[-1]
                page.goto(real_url, wait_until="load")
                page.wait_for_timeout(WAIT_MS)
                print(f"  page title: {page.title()!r}")
                print(f"  body text[:1500]: {page.inner_text('body')[:1500]!r}")
            else:
                print("  no https:// URL found in href, skipping navigation")
            ctx.close()

        def ropes_gray():
            section("Ropes & Gray -- clicking through to US Careers")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            candidates = []

            def on_resp(r):
                ct = r.headers.get("content-type", "")
                if "json" in ct.lower() or re.search(r"job|career|search|api", r.url, re.I):
                    if not any(n in r.url.lower() for n in ["gtm.js", "analytics", ".woff", ".css", ".png", ".jpg", ".svg", "cookielaw", "onetrust"]):
                        candidates.append((r.url, r.status, ct))

            page.on("response", on_resp)
            page.goto("https://www.ropesgrayrecruiting.com/en/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            try:
                page.get_by_text("US CAREERS", exact=False).first.click(timeout=5000)
                page.wait_for_timeout(WAIT_MS)
                print("  clicked 'US CAREERS'")
            except Exception as exc:
                print(f"  could not click US CAREERS: {exc}")
            print(f"  page title after click: {page.title()!r}")
            print(f"  current URL: {page.url}")
            for url, status, ct in candidates[:20]:
                print(f"    [{status}] {ct} {url}")
            print(f"  body text[:1200]: {page.inner_text('body')[:1200]!r}")
            ctx.close()

        run_safely("Paul Weiss", paul_weiss)
        run_safely("Duane Morris", duane_morris)
        run_safely("Crowell & Moring", crowell_moring)
        run_safely("Ropes & Gray", ropes_gray)

        browser.close()


if __name__ == "__main__":
    main()
