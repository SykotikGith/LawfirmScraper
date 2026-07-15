"""Category 2, round 8 -- Kirkland & Ellis pagination + real row markup.

McDermott is done (McDermottAdapter added -- plain Algolia POST, no
Playwright needed, see mcdermott.py).

Round 7 confirmed /jobs/search/ (trailing slash) shows ALL 155 jobs
unfiltered in one page load rather than needing to loop over ~13 city
facets, but only 25 job links were found on initial load -- this finds
out whether that's real pagination (a page=N URL param, numbered page
links) or a "load more"/infinite-scroll pattern, and grabs the real
per-row DOM structure (title link, category, location, posted date) so
a clean selector-based Playwright adapter can be built instead of
regexing loose body text.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

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
            section("Kirkland & Ellis -- pagination + real row markup")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/jobs/search/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            # Look for pagination controls.
            for sel in [
                "a[href*='page=']", "[class*='pagination'] a", "[class*='pager'] a",
                "a:has-text('Next')", "a:has-text('2')", "button:has-text('Load More')",
                "button:has-text('Show More')",
            ]:
                els = page.query_selector_all(sel)
                if els:
                    print(f"  selector {sel!r}: {len(els)} elements")
                    for el in els[:5]:
                        try:
                            print(f"    href={el.get_attribute('href')!r} text={el.inner_text()!r}")
                        except Exception:
                            pass

            # Try an explicit page=2 URL guess.
            page2 = ctx.new_page()
            page2.goto("https://staffjobsus.kirkland.com/jobs/search/?page=2", wait_until="load")
            page2.wait_for_timeout(WAIT_MS)
            links2 = page2.query_selector_all("a[href*='staffjobsus.kirkland.com/jobs/']")
            print(f"  ?page=2 real job links found: {len(links2)}")
            if links2:
                print(f"    first: {links2[0].get_attribute('href')!r} {links2[0].inner_text()!r}")

            # Real row markup for the first job on page 1.
            first_link = page.query_selector("a[href*='staffjobsus.kirkland.com/jobs/']")
            if first_link:
                row = first_link.evaluate_handle(
                    "el => el.closest('tr') || el.closest('li') || el.closest('div')"
                )
                row_html = row.evaluate("el => el ? el.outerHTML : null")
                print(f"  first row outerHTML[:2500]: {row_html[:2500] if row_html else None!r}")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)

        browser.close()


if __name__ == "__main__":
    main()
