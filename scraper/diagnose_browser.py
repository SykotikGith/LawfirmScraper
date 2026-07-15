"""Category 2, round 4 -- getting exact adapter-ready shapes for both.

- Kirkland & Ellis: round 3 confirmed the Chicago-filtered results page
  renders real job rows (title, category, location, posted date) in
  plain visible text -- this finds the actual DOM structure (row
  elements + per-job href) so a real adapter can target precise
  selectors instead of parsing loose body text, and checks whether
  there's an unfiltered "View All Jobs" URL so the adapter doesn't need
  to loop over every location facet separately.
- McDermott: round 3 found the real job data comes from a public
  Algolia index (mws_posts_jobs) called directly from the browser with
  an x-algolia-api-key that's exposed client-side by design (standard
  Algolia InstantSearch pattern, not a security bypass) -- this
  captures the exact request/response shape (method, headers, body)
  needed to replicate the call with plain `requests`, no Playwright
  needed at all if it works.

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
            section("Kirkland & Ellis -- exact row DOM + all-jobs URL")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/search/jobs/in/chicago", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            first_link = page.query_selector("a[href*='/jobs/']")
            if first_link:
                row = first_link.evaluate_handle(
                    "el => el.closest('tr') || el.closest('li') || el.closest('div.job-result') || el.parentElement.parentElement"
                )
                row_html = row.evaluate("el => el ? el.outerHTML : null")
                print(f"  row outerHTML[:2000]: {row_html[:2000] if row_html else None!r}")
                print(f"  first job link href: {first_link.get_attribute('href')!r}")

            all_jobs_link = page.query_selector("a:has-text('View All Jobs')")
            if all_jobs_link:
                print(f"  'View All Jobs' href: {all_jobs_link.get_attribute('href')!r}")
            else:
                print("  no 'View All Jobs' link found on this page")

            # Try the bare, unfiltered search page and check job count there.
            page2 = ctx.new_page()
            page2.goto("https://staffjobsus.kirkland.com/jobs/search", wait_until="load")
            page2.wait_for_timeout(WAIT_MS)
            body2 = page2.inner_text("body")
            idx = body2.find("Jobs Found")
            print(f"  /jobs/search body near 'Jobs Found': {body2[max(0,idx-50):idx+50]!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- capturing the raw Algolia request/response")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            captured = []

            def on_resp(r):
                if "algolia" in r.url.lower() and "query" in r.url.lower():
                    try:
                        body = r.request.post_data
                        resp_json = r.json() if r.ok else None
                    except Exception as exc:
                        body = f"<error reading: {exc}>"
                        resp_json = None
                    captured.append((r.request.method, r.url, r.request.headers, body, resp_json))

            page.on("response", on_resp)
            page.goto("https://www.mcdermottlaw.com/careers/open-roles/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            for method, url, headers, body, resp_json in captured[:3]:
                print(f"  {method} {url}")
                print(f"    request headers: {dict(headers)}")
                print(f"    request body: {body!r}")
                if resp_json:
                    hits = resp_json.get("results", [{}])[0].get("hits", resp_json.get("hits", []))
                    print(f"    response hit count: {len(hits)}")
                    if hits:
                        print(f"    sample hit keys: {list(hits[0].keys())}")
                        print(f"    sample hit: {hits[0]!r}")
                print()
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
