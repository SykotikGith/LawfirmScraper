"""Round 4 -- the remaining 5 unresolved Category 1 firms.

- Venable: 2 rounds of replaying the real ADP endpoint (fresh context,
  then within an established session) both 400'd -- something beyond
  cookies is required (a CSRF token, a specific header). Rather than
  keep fighting that, this reads the actual rendered job cards directly
  from the DOM instead, which round 1 confirmed shows real jobs
  ("Conflicts Attorney" etc.) once the page settles.
- Paul Weiss: round 3's generic link selectors grabbed UI chrome (a
  search-callout tooltip icon), not real job rows -- this looks
  specifically for repeated row elements matching Taleo's
  "requisitionListInterface"-style naming convention.
- Duane Morris: round 3's capture got cut off right before the actual
  "Current Opportunities" links list -- this grabs a wider slice
  specifically around that heading.
- Crowell & Moring: round 3 found the Open Positions link's href was
  corrupted (a literal markdown-style "[text](url)" string stored as the
  href attribute, not a real URL) -- this extracts the real URL from
  inside it and follows that instead.
- Ropes & Gray: the real recruiting domain (ropesgrayrecruiting.com) is
  a marketing landing page with no job data yet -- this clicks through
  to "US Careers" and captures whatever loads next.

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


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Venable: read rendered job cards directly ---
        section("Venable -- reading rendered job cards from the DOM")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://myjobs.adp.com/venablebusinessprofessionalcareers/cx", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        # Try to find a repeated card/row structure around a known job title.
        handle = page.query_selector("text=Conflicts Attorney")
        if handle:
            card = handle.evaluate_handle(
                "el => el.closest('[class*=card], [class*=job], [class*=row], li, article')"
            )
            card_html = card.evaluate("el => el ? el.outerHTML : null")
            print(f"  closest card-like ancestor outerHTML[:1500]: {card_html[:1500] if card_html else None!r}")
        else:
            print("  'Conflicts Attorney' text not found this time")
        # Also count how many similarly-structured elements exist (for a selector guess).
        counts = page.evaluate(
            "() => { const sel = ['[class*=job-card]','[class*=jobCard]','[class*=requisition]','[class*=job-tile]']; "
            "return sel.map(s => [s, document.querySelectorAll(s).length]); }"
        )
        print(f"  candidate selector counts: {counts}")
        ctx.close()

        # --- Paul Weiss: find real requisitionList-style rows ---
        section("Paul Weiss -- hunting for requisitionListInterface-style rows")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        try:
            page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
        except Exception as exc:
            print(f"  could not click Search: {exc}")
        page.wait_for_timeout(WAIT_MS)
        req_links = page.query_selector_all("a[id*='reqTitle'], a[id*='requisitionList']")
        print(f"  a[id*='reqTitle' or 'requisitionList'] count: {len(req_links)}")
        for link in req_links[:5]:
            print(f"    id={link.get_attribute('id')!r} text={link.inner_text()!r} href={link.get_attribute('href')!r}")
        # Broader: any element whose id contains "requisitionList"
        any_req = page.query_selector_all("[id*='requisitionList']")
        print(f"  any [id*='requisitionList'] count: {len(any_req)}")
        for el in any_req[:8]:
            print(f"    tag={el.evaluate('e => e.tagName')!r} id={el.get_attribute('id')!r} text={el.inner_text()[:80]!r}")
        ctx.close()

        # --- Duane Morris: wider slice around Current Opportunities ---
        section("Duane Morris -- wider capture around Current Opportunities links")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.duanemorris.com/site/careers.html", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        body_text = page.inner_text("body")
        idx = body_text.find("Current Opportunities")
        print(f"  text around 'Current Opportunities'[{idx}:{idx+1500}]:")
        print(body_text[idx:idx + 1500])
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.filter(e => /opportunit|position|staff/i.test(e.href) || /opportunit|position/i.test(e.textContent))"
            ".map(e => [e.textContent.trim(), e.href])",
        )
        print(f"  opportunity/position-related links: {links[:15]}")
        ctx.close()

        # --- Crowell & Moring: fix the malformed href and follow it ---
        section("Crowell & Moring -- following the corrected Open Positions URL")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.crowell.com/en/careers/professional-staff", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        link = page.get_by_text("Open Positions", exact=False).first
        raw_href = link.get_attribute("href")
        print(f"  raw href: {raw_href!r}")
        match = re.search(r"\((https?://[^)]+)\)", raw_href or "")
        real_url = match.group(1) if match else raw_href
        print(f"  extracted real URL: {real_url!r}")
        if real_url:
            page.goto(real_url, wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  page title: {page.title()!r}")
            print(f"  body text[:1500]: {page.inner_text('body')[:1500]!r}")
        ctx.close()

        # --- Ropes & Gray: click through to US Careers ---
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

        browser.close()


if __name__ == "__main__":
    main()
