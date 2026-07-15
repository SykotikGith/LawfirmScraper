"""Category 2, round 9 -- Kirkland & Ellis: click-through pagination + full row markup.

Round 8 confirmed real pagination (page=2..6 links, "NEXT" button) but
a direct .goto() to a guessed page=2 URL returned zero real job links --
likely because the real pagination href
(/jobs/search?page=2#, NO trailing slash) differs subtly from the
trailing-slash form that's known to render cleanly
(/jobs/search/), and this site's Cloudflare rule appears to gate on
exact path. Clicking the real "NEXT" link from within the
already-passed session (matching real browsing behavior) should avoid
that entirely, since it's the same navigation a real visitor performs.

Round 8 also only captured the title sub-div (class
"jobs-section__item-title"), not the full row with category/location/
date -- this looks for the outer row container (likely class
"jobs-section__item" without the "-title" suffix) to get the complete
per-job markup.

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
            section("Kirkland & Ellis -- click-through pagination + full row markup")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/jobs/search/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            all_hrefs = set()
            for page_num in range(1, 8):
                links = page.query_selector_all("a[href*='staffjobsus.kirkland.com/jobs/']")
                new_count = 0
                for link in links:
                    href = link.get_attribute("href")
                    if href and href not in all_hrefs:
                        all_hrefs.add(href)
                        new_count += 1
                print(f"  page {page_num}: {len(links)} links on page, {new_count} new, {len(all_hrefs)} total so far")

                next_link = page.query_selector("a:has-text('NEXT')")
                if not next_link:
                    print("  no NEXT link found, stopping")
                    break
                try:
                    next_link.click(timeout=5000)
                    page.wait_for_timeout(WAIT_MS)
                except Exception as exc:
                    print(f"  could not click NEXT: {exc}")
                    break

            print(f"  FINAL total unique job links collected: {len(all_hrefs)}")

            # Full row markup for whatever's on the current page.
            title_div = page.query_selector("[class*='jobs-section__item-title']")
            if title_div:
                row = title_div.evaluate_handle(
                    "el => el.closest('[class*=\"jobs-section__item\"]:not([class*=\"item-title\"])') || el.parentElement"
                )
                row_html = row.evaluate("el => el ? el.outerHTML : null")
                print(f"  full row outerHTML[:3000]: {row_html[:3000] if row_html else None!r}")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)

        browser.close()


if __name__ == "__main__":
    main()
