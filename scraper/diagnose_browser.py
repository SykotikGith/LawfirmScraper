"""Category 2, round 6.

- Kirkland & Ellis: confirmed the "BROWSE JOBS" nav href
  (/jobs/search/?sort_by=...) hits the HARD Cloudflare challenge ("Just
  a moment...") -- only the location-filtered URLs (/search/jobs/in/
  <city>) pass cleanly, consistent with round 3. But round 5 found zero
  a[href*='/job/'] links on that page, meaning job title links don't
  use that URL pattern at all. This dumps every <a> href inside the
  results table/list (no pattern filter) to find the real per-job link
  format, or confirms there isn't one (JS-only row click, same
  postback-only situation as some viGlobal tenants).
- McDermott: round 5 only captured 2 Algolia calls total, neither
  printed (meaning both were still hitsPerPage:0 facet queries, or the
  real hits query fires later than the wait window). This waits longer
  and dumps EVERY captured Algolia call's body/response unconditionally
  (not just ones that already parsed as having hits), to see the full
  picture and catch a possible response-shape parsing mismatch.

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
            section("Kirkland & Ellis -- every <a href> on the Chicago results page")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto("https://staffjobsus.kirkland.com/search/jobs/in/chicago", wait_until="load")
            page.wait_for_timeout(WAIT_MS)

            all_links = page.query_selector_all("a[href]")
            print(f"  total <a href> on page: {len(all_links)}")
            seen = set()
            for link in all_links:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()
                if href in seen:
                    continue
                seen.add(href)
                if text and len(text) > 3 and "javascript:" not in href.lower():
                    print(f"    href={href!r} text={text[:60]!r}")
            ctx.close()

        def mcdermott():
            section("McDermott -- every Algolia call, unconditionally")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            captured = []

            def on_resp(r):
                if "algolia" in r.url.lower():
                    try:
                        body = r.request.post_data
                        resp_json = r.json() if r.ok else None
                    except Exception as exc:
                        body = f"<error reading: {exc}>"
                        resp_json = f"<error: {exc}>"
                    captured.append((r.request.method, r.url, body, resp_json))

            page.on("response", on_resp)
            page.goto("https://www.mcdermottlaw.com/careers/open-roles/", wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(WAIT_MS)

            print(f"  total Algolia calls captured: {len(captured)}")
            for i, (method, url, body, resp_json) in enumerate(captured):
                print(f"  [{i}] {method} {url[:120]}")
                print(f"      body: {body!r}")
                if isinstance(resp_json, dict):
                    print(f"      response top-level keys: {list(resp_json.keys())}")
                    print(f"      response[:800]: {str(resp_json)[:800]!r}")
                else:
                    print(f"      response: {resp_json!r}")
            ctx.close()

        run_safely("Kirkland & Ellis", kirkland)
        run_safely("McDermott", mcdermott)

        browser.close()


if __name__ == "__main__":
    main()
