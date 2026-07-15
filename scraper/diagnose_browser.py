"""Category 2, round 5 -- fixing two round-4 diagnostic mistakes.

- Kirkland & Ellis: round 4's a[href*='/jobs/'] selector matched the
  first link in DOM order, which turned out to be the "BROWSE JOBS" nav
  item, not a real job row -- not useful. This narrows to a[href*=
  '/job/'] (singular -- detail pages, not the /jobs/ nav/listing URLs)
  to find real per-posting links, and also tries the exact "BROWSE
  JOBS" nav href with its sort_by param and trailing slash
  (/jobs/search/?sort_by=cfml10%2Cdesc) -- possibly the real unfiltered
  "all jobs" view, since the bare no-trailing-slash /jobs/search hit a
  harder "Performing security verification" Cloudflare challenge that
  the trailing-slash variant didn't.
- McDermott: round 4 only captured the first 3 Algolia calls, which
  turned out to be hitsPerPage:0 facet-count queries (building filter
  UI), not the real search returning actual job hits. This captures
  every Algolia call and prints only the ones with a nonzero hit count
  or hitsPerPage > 0, to find the real query shape.

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
            section("Kirkland & Ellis -- real job detail links + BROWSE JOBS nav href")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/search/jobs/in/chicago", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            job_links = page.query_selector_all("a[href*='/job/']")
            print(f"  a[href*='/job/'] count: {len(job_links)}")
            if job_links:
                link = job_links[0]
                print(f"  first real job link href: {link.get_attribute('href')!r}")
                print(f"  first real job link text: {link.inner_text()!r}")
                row = link.evaluate_handle(
                    "el => el.closest('tr') || el.closest('li') || el.closest('div')"
                )
                row_html = row.evaluate("el => el ? el.outerHTML : null")
                print(f"  containing row outerHTML[:2000]: {row_html[:2000] if row_html else None!r}")

            page2 = ctx.new_page()
            page2.goto(
                "https://staffjobsus.kirkland.com/jobs/search/?sort_by=cfml10%2Cdesc",
                wait_until="load",
            )
            page2.wait_for_timeout(WAIT_MS)
            body2 = page2.inner_text("body")
            idx = body2.find("Jobs Found")
            print(f"  BROWSE JOBS page near 'Jobs Found': {body2[max(0,idx-80):idx+80]!r}")
            print(f"  BROWSE JOBS page title: {page2.title()!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- finding the real Algolia hits query")
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

            print(f"  total Algolia calls captured: {len(captured)}")
            for method, url, headers, body, resp_json in captured:
                hits = []
                if resp_json:
                    if "results" in resp_json:
                        hits = resp_json["results"][0].get("hits", [])
                    else:
                        hits = resp_json.get("hits", [])
                if hits:
                    print(f"  {method} {url}")
                    print(f"    request body: {body!r}")
                    print(f"    hit count: {len(hits)}")
                    print(f"    sample hit keys: {list(hits[0].keys())}")
                    print(f"    sample hit: {hits[0]!r}")
                    print()
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
