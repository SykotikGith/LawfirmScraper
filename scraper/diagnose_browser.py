"""Category 2, round 10 -- confirming what actually happens on Kirkland page 2.

Round 9's click on "NEXT" landed on a page with zero real job links and
no further NEXT link -- consistent with the theory that ANY navigation
to /jobs/search (no trailing slash), even via a real click rather than
a guessed .goto() URL, hits the same hard Cloudflare "Just a moment..."
challenge that the trailing-slash form doesn't. This just confirms that
directly: click NEXT once, then dump the resulting page's title/URL/
body to see if it's really the challenge page.

If confirmed, page 1 (25 of 155 real postings) is the ceiling for this
firm without deeper Cloudflare-challenge-solving work this project
isn't going to attempt (per the "don't force it" instruction) -- 25
real postings is still a genuine, usable partial result, better than
no automation at all, similar to Akin Gump's already-documented
pagination gap.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

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
            section("Kirkland & Ellis -- what's really on page 2 after clicking NEXT")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/jobs/search/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            next_link = page.query_selector("a:has-text('NEXT')")
            if next_link:
                href_before = next_link.get_attribute("href")
                print(f"  NEXT href: {href_before!r}")
                next_link.click(timeout=5000)
                page.wait_for_timeout(WAIT_MS)
                print(f"  URL after click: {page.url}")
                print(f"  title after click: {page.title()!r}")
                body = page.inner_text("body")
                print(f"  body text[:1000]: {body[:1000]!r}")
            else:
                print("  no NEXT link found on page 1")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)

        browser.close()


if __name__ == "__main__":
    main()
