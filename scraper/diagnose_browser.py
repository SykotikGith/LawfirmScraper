"""Round 8 -- last firm standing: Duane Morris.

Paul Weiss and Crowell & Moring are done (PaulWeissAdapter added as a
genuine runtime PlaywrightAdapter; Crowell & Moring turned out to be
plain Greenhouse, board_token=crowellmoring).

Duane Morris's per-city job links found in round 7
(selfapply.duanemorris.com/viselfapply/viRecruitSelfApply/RecDefault.aspx
?FilterREID=2&FilterJobCategoryID=22&FilterJobID=492) are the exact same
viRecruitSelfApply URL pattern this project's ViGlobalAdapter already
handles for O'Melveny, Bryan Cave, Vinson & Elkins, Bracewell, and Mintz
-- meaning Duane Morris may not need Playwright OR a new adapter at all,
just a ViGlobalAdapter config entry. This checks two things with a
*plain, no-JS* HTTP request (ctx.request.get, not page.goto) to confirm
that's really true and not just how it renders after JS runs:

1. Does .../viRecruitSelfApply/RecDefault.aspx?FilterREID=2 (guessed,
   same FilterREID=2 seen in the per-job hrefs, no job-specific filter)
   return a real GridView table (id=contentPlaceHolder_gridviewList)
   with real rows, via plain HTTP with zero JS execution?
2. What shape are the rows in -- one of the two shapes ViGlobalAdapter
   already knows how to parse (structured <h4>/<h5> tags, or an
   O'Melveny-style mashed text blob), or something new?

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


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

        def duane_morris():
            section("Duane Morris -- plain HTTP (no JS) fetch of guessed viGlobal list URL")
            ctx = browser.new_context(user_agent=UA)
            for guess in [
                "https://selfapply.duanemorris.com/viselfapply/viRecruitSelfApply/RecDefault.aspx?FilterREID=2",
                "https://selfapply.duanemorris.com/viselfapply/viRecruitSelfApply/RecDefault.aspx",
            ]:
                resp = ctx.request.get(guess, timeout=15000)
                print(f"  {guess}")
                print(f"    status: {resp.status}")
                body = resp.text()
                print(f"    body length: {len(body)}")
                has_table = "contentPlaceHolder_gridviewList" in body
                print(f"    has contentPlaceHolder_gridviewList table: {has_table}")
                if has_table:
                    idx = body.find("contentPlaceHolder_gridviewList")
                    print(f"    table region[:3000]: {body[idx:idx+3000]!r}")
            ctx.close()

        run_safely("Duane Morris", duane_morris)

        browser.close()


if __name__ == "__main__":
    main()
