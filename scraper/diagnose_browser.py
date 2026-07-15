"""Round 3.

- Venable: round 2 found the real ADP endpoint 400s without an established
  session -- this visits the page first (in the same browser context, so
  cookies get set), then tries the $skip pagination from within that
  session to see if it works once cookies are present.
- Paul Weiss: round 2 got real data back from jobsearch.ajax, but in
  Taleo's proprietary pipe-delimited internal format, not JSON -- rather
  than reverse-engineering that fragile format, this reads the actual
  rendered results table after the search completes (real HTML, stable
  class names) to find a CSS selector to scrape directly.
- Kramer Levin: round 2 confirmed real job text IS present in the raw
  pre-JS HTML -- this looks for the actual surrounding markup/structure
  (or an embedded JSON blob) so a plain HTTP+HTML adapter can be built,
  no Playwright needed at runtime.
- Duane Morris: round 2's plain click didn't find a real href for
  "Support Staff Opportunities" -- this retries with the ORIGINAL
  #tab_SupportStaffOpportunities URL fragment the user originally gave,
  since tab widgets often read the hash on page load to auto-select a
  panel.
- Crowell & Moring: followed to /en/careers/professional-staff last
  round, which is just an overview page with an "Open Positions" link
  still unfollowed -- this finds and follows it.
- Ropes & Gray: round 2 found the real domain is ropesgrayrecruiting.com
  (not ropesgray.com at all) -- this investigates it from scratch.
- Vinson & Elkins: the original Tag= URL redirected to the plain
  homepage, and a narrow link search on the real careers page found
  nothing -- this dumps ALL links/iframes on that page much more broadly
  to find wherever the live Apply/job-board link actually lives now.
- Akin Gump: round 2 confirmed real job text IS present in the raw
  pre-JS HTML (no JSON script tag, so presumably real server-rendered
  HTML) -- this looks for the actual surrounding markup.

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

        # --- Venable: pagination within an established session ---
        section("Venable -- pagination within an established browser session")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://myjobs.adp.com/venablebusinessprofessionalcareers/cx", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        base = (
            "https://my.adp.com/myadp_prefix/mycareer/public/staffing/v1/job-requisitions/list-view"
            "?$orderby=postingDate%20desc&$select=reqId,jobTitle,publishedJobTitle,type,"
            "jobDescription,jobQualifications,workLocations,workLevelCode,clientRequisitionID,"
            "postingDate,requisitionLocations&$top=10&tz=America/Chicago"
        )
        resp = page.request.get(base)
        print(f"  page1 (within session) -> status={resp.status}")
        if resp.status == 200:
            data = resp.json()
            print(f"  count={data.get('count')}")
        resp2 = page.request.get(base.replace("$top=10", "$top=10&$skip=10"))
        print(f"  $skip=10 (within session) -> status={resp2.status}")
        if resp2.status == 200:
            data2 = resp2.json()
            titles = [j.get("requisitionTitle") for j in data2.get("jobRequisitions", [])]
            print(f"  titles on page 2: {titles}")
        ctx.close()

        # --- Paul Weiss: read the rendered results table after search ---
        section("Paul Weiss -- reading the rendered results table")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        try:
            page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
        except Exception as exc:
            print(f"  could not click Search: {exc}")
        page.wait_for_timeout(WAIT_MS)
        rows = page.query_selector_all("tr")
        print(f"  total <tr> elements on page: {len(rows)}")
        job_link = page.query_selector("a[id*='reqTitleLink'], a[id*='jobTitle'], td a")
        if job_link:
            print(f"  sample link: id={job_link.get_attribute('id')!r} text={job_link.inner_text()!r}")
            row = job_link.evaluate_handle("el => el.closest('tr')")
            row_html = row.evaluate("el => el ? el.outerHTML : null")
            print(f"  closest <tr> outerHTML[:1500]: {row_html[:1500] if row_html else None!r}")
        else:
            print("  no obvious job link found via generic selectors")
        ctx.close()

        # --- Kramer Levin: find the real markup around the embedded job data ---
        section("Kramer Levin -- markup around the embedded job data")
        ctx = browser.new_context(user_agent=UA)
        resp = ctx.request.get("https://careers.hsfkramer.com/global/en/us/search-results")
        raw = resp.text()
        idx = raw.find("Help Desk Technician")
        print(f"  context around 'Help Desk Technician'[{max(0,idx-800)}:{idx+800}]:")
        print(raw[max(0, idx - 800):idx + 800])
        ctx.close()

        # --- Duane Morris: retry with the original hash fragment ---
        section("Duane Morris -- retrying with #tab_SupportStaffOpportunities")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(
            "https://www.duanemorris.com/site/careers.html#tab_SupportStaffOpportunities",
            wait_until="load",
        )
        page.wait_for_timeout(WAIT_MS)
        panel = page.query_selector("#tab_SupportStaffOpportunities")
        print(f"  #tab_SupportStaffOpportunities element found: {panel is not None}")
        if panel:
            print(f"  panel inner text[:1500]: {panel.inner_text()[:1500]!r}")
        print(f"  full body text[:1200]: {page.inner_text('body')[:1200]!r}")
        ctx.close()

        # --- Crowell & Moring: follow Open Positions ---
        section("Crowell & Moring -- following Open Positions")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.crowell.com/en/careers/professional-staff", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        link = page.get_by_text("Open Positions", exact=False).first
        href = link.get_attribute("href")
        print(f"  href of 'Open Positions' link: {href!r}")
        if href:
            full_url = href if href.startswith("http") else f"https://www.crowell.com{href}"
            page.goto(full_url, wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  navigated to {full_url}")
            print(f"  page title: {page.title()!r}")
            print(f"  body text[:1200]: {page.inner_text('body')[:1200]!r}")
        ctx.close()

        # --- Ropes & Gray: investigate the new recruiting domain ---
        section("Ropes & Gray -- investigating ropesgrayrecruiting.com")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        candidates = []

        def on_resp(r):
            ct = r.headers.get("content-type", "")
            if "json" in ct.lower() or re.search(r"job|career|search|api", r.url, re.I):
                if not any(n in r.url.lower() for n in ["gtm.js", "analytics", ".woff", ".css", ".png", ".jpg", ".svg"]):
                    candidates.append((r.url, r.status, ct))

        page.on("response", on_resp)
        page.goto("https://www.ropesgrayrecruiting.com/en/", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        print(f"  page title: {page.title()!r}")
        for url, status, ct in candidates[:20]:
            print(f"    [{status}] {ct} {url}")
        print(f"  body text[:1200]: {page.inner_text('body')[:1200]!r}")
        ctx.close()

        # --- Vinson & Elkins: broad link/iframe dump on the real careers page ---
        section("Vinson & Elkins -- broad link/iframe dump")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.velaw.com/careers/business-professionals/", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        all_links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => [e.textContent.trim(), e.href]).filter(x => x[1] && !x[1].endsWith('#'))"
        )
        print(f"  all non-# links found: {len(all_links)}")
        for text, href in all_links:
            print(f"    {text!r} -> {href}")
        iframes = page.eval_on_selector_all("iframe", "els => els.map(e => e.src)")
        print(f"  iframes: {iframes}")
        ctx.close()

        # --- Akin Gump: markup around the embedded job data ---
        section("Akin Gump -- markup around the embedded job data")
        ctx = browser.new_context(user_agent=UA)
        resp = ctx.request.get("https://jobs.silkroad.com/AkinGump/AkinGump")
        raw = resp.text()
        idx = raw.find("Litigation Practice Coordinator")
        print(f"  context around 'Litigation Practice Coordinator'[{max(0,idx-800)}:{idx+800}]:")
        print(raw[max(0, idx - 800):idx + 800])
        ctx.close()

        browser.close()


if __name__ == "__main__":
    main()
