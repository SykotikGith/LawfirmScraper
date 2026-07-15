"""Round 7 -- closing out the last 3 firms.

- Paul Weiss: round 6 confirmed 11 real rows with title, requisition ID,
  work location, schedule, and posting date, but no real per-job href
  (postback-only JS). Classic Taleo Enterprise career sections commonly
  serve a separate detail page at
  careersection/<section>/jobdetail.ftl?job=<requisitionID> -- this
  tries that guessed URL for row1's requisition ID (26000223) to see if
  it's a real, working, linkable detail page.
- Duane Morris: round 6 confirmed the city names are Bootstrap-style
  accordion toggles (href="#collapse-atlanta" etc.), not page
  navigations. Bootstrap accordions typically have their panel content
  already present in the raw server-rendered HTML, just hidden by CSS
  until expanded -- this checks whether div#collapse-atlanta (and a
  couple others) already contain real job links in the DOM without
  needing to click anything, which would mean a plain requests +
  BeautifulSoup adapter works with zero JS execution needed.
- Crowell & Moring: round 6 confirmed the site embeds Greenhouse
  (for=crowellmoring), but via the newer job-boards.greenhouse.io embed
  UI with a validityToken, not the classic public REST API this project
  already has a GreenhouseAdapter for. This checks whether the classic
  https://boards-api.greenhouse.io/v1/boards/crowellmoring/jobs endpoint
  (same one GreenhouseAdapter already calls for other firms) is also
  live for this token -- if so, no new adapter is needed, just a config
  entry.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

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
            section("Paul Weiss -- guessed Taleo jobdetail.ftl URL for requisition 26000223")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            for guess in [
                "https://paulweiss.taleo.net/careersection/ex/jobdetail.ftl?job=26000223",
                "https://paulweiss.taleo.net/careersection/ex/jobdetail.ftl?job=26000223&lang=en",
            ]:
                try:
                    resp = page.goto(guess, wait_until="load")
                    print(f"  {guess}")
                    print(f"    status: {resp.status if resp else None}")
                    print(f"    title: {page.title()!r}")
                    body = page.inner_text("body")
                    idx = body.find("Business Services Assistant")
                    print(f"    'Business Services Assistant' found at index {idx}")
                    if idx != -1:
                        print(f"    context: {body[max(0, idx-100):idx+300]!r}")
                except Exception as exc:
                    print(f"    EXCEPTION: {type(exc).__name__}: {exc}")
            ctx.close()

        def duane_morris():
            section("Duane Morris -- checking accordion panel content in raw DOM")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto(
                "https://www.duanemorris.com/site/careers.html#SupportStaffOpportunities",
                wait_until="load",
            )
            page.wait_for_timeout(WAIT_MS)
            for panel_id in ["collapse-atlanta", "collapse-multiple", "collapse-newyork"]:
                el = page.query_selector(f"#{panel_id}")
                if el is None:
                    print(f"  #{panel_id}: not found in DOM")
                    continue
                text = el.inner_text().strip()
                links = el.query_selector_all("a")
                print(f"  #{panel_id}: inner_text[:800]={text[:800]!r}")
                print(f"  #{panel_id}: {len(links)} <a> tags")
                for link in links[:10]:
                    print(f"      href={link.get_attribute('href')!r} text={link.inner_text()!r}")
            ctx.close()

        def crowell_moring():
            section("Crowell & Moring -- testing the classic Greenhouse public API")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            api_url = "https://boards-api.greenhouse.io/v1/boards/crowellmoring/jobs?content=true"
            resp = ctx.request.get(api_url, timeout=15000)
            print(f"  {api_url}")
            print(f"  status: {resp.status}")
            if resp.ok:
                data = resp.json()
                jobs = data.get("jobs", [])
                print(f"  total jobs: {len(jobs)}")
                for job in jobs[:8]:
                    print(f"    {job.get('title')!r} | {(job.get('location') or {}).get('name')!r}")
            else:
                print(f"  body[:500]: {resp.text()[:500]!r}")
            ctx.close()

        run_safely("Paul Weiss", paul_weiss)
        run_safely("Duane Morris", duane_morris)
        run_safely("Crowell & Moring", crowell_moring)

        browser.close()


if __name__ == "__main__":
    main()
