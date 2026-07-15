"""Round 2: follow-ups on what round 1 found.

Two firms already have a clean public JSON API confirmed (Sheppard
Mullin, Venable) -- this just double-checks pagination/completeness
before building a normal HTTP adapter for them (no Playwright needed at
runtime). Dentons has a classic ASP.NET .asmx endpoint whose body wasn't
captured last round (empty content-type in the log). The rest need one
more navigation step: Paul Weiss's real results likely come back from
jobsearch.ajax after a search is actually triggered; Duane Morris and
Crowell & Moring's Business/Professional Staff links go to separate
pages round 1 never followed; Ropes & Gray's known URLs both 404/don't
exist anymore, so this hunts the real one; Vinson & Elkins' Tag= URL
redirected to the plain homepage instead of the job board, suggesting
the GUID has expired -- this looks for a fresh one on the real careers
page; Akin Gump's job data never showed up as a captured API call, so
this checks whether it's actually embedded in the raw page response
(server-rendered) rather than genuinely client-fetched, which would mean
no Playwright is needed for it either; Kramer Levin's rendered jobs
didn't line up with any captured API response either, so same check.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
NAV_TIMEOUT_MS = 30_000
WAIT_MS = 4_000


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Sheppard Mullin: confirm full result count / pagination ---
        section("Sheppard Mullin -- checking career-page-jobs API completeness")
        ctx = browser.new_context(user_agent=UA)
        resp = ctx.request.get(
            "https://florecruit.com/api/v2/public-jobs/sheppardbusinessservices/career-page-jobs"
        )
        print(f"  status={resp.status}")
        try:
            data = resp.json()
            print(f"  total postings returned: {len(data)}")
            for job in data[:20]:
                print(f"    - {job.get('title')!r}")
        except Exception as exc:
            print(f"  JSON parse failed: {exc}; body[:300]={resp.text()[:300]!r}")
        ctx.close()

        # --- Venable: confirm the ADP endpoint works standalone + pagination ---
        section("Venable -- checking my.adp.com job-requisitions endpoint standalone + pagination")
        ctx = browser.new_context(user_agent=UA)
        base = (
            "https://my.adp.com/myadp_prefix/mycareer/public/staffing/v1/job-requisitions/list-view"
            "?$orderby=postingDate%20desc&$select=reqId,jobTitle,publishedJobTitle,type,"
            "jobDescription,jobQualifications,workLocations,workLevelCode,clientRequisitionID,"
            "postingDate,requisitionLocations&$top=10&tz=America/Chicago"
        )
        resp = ctx.request.get(base)
        print(f"  fresh-context GET (no prior page visit) -> status={resp.status}")
        if resp.status == 200:
            data = resp.json()
            print(f"  count={data.get('count')}, jobRequisitions returned={len(data.get('jobRequisitions', []))}")
        resp2 = ctx.request.get(base.replace("$top=10", "$top=10&$skip=10"))
        print(f"  $skip=10 page -> status={resp2.status}")
        if resp2.status == 200:
            data2 = resp2.json()
            titles = [j.get("requisitionTitle") for j in data2.get("jobRequisitions", [])]
            print(f"  titles on page 2: {titles}")
        ctx.close()

        # --- Dentons: fetch the .asmx endpoint directly, see the real body ---
        section("Dentons -- fetching GetJobsByState directly")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(
            "https://www.dentons.com/en/careers/careers-in-the-united-states/business-services-in-the-united-states/",
            wait_until="load",
        )
        page.wait_for_timeout(WAIT_MS)
        asmx_url = (
            "https://www.dentons.com/DentonsServices/career.asmx/GetJobsByState"
            "?officeID=&pageSize=20&pageNumber=1"
            "&contextItem={4CCB9477-3A1B-4C92-8FB9-6282C913B18D}"
            "&contextItemUrl=https://www.dentons.com/en/careers/careers-in-the-united-states/business-services-in-the-united-states/"
            "&contextLanguage=en&contextSite=dentons"
        )
        resp = page.request.get(asmx_url)
        print(f"  status={resp.status}  content-type={resp.headers.get('content-type')}")
        print(f"  body[:1500]: {resp.text()[:1500]!r}")
        ctx.close()

        # --- Paul Weiss: actually trigger a search, capture jobsearch.ajax body ---
        section("Paul Weiss -- triggering a real search, capturing jobsearch.ajax")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        ajax_bodies = []

        def on_resp(r):
            if "jobsearch.ajax" in r.url or "searchjobs" in r.url.lower():
                try:
                    ajax_bodies.append((r.url, r.status, r.text()[:2000]))
                except Exception:
                    pass

        page.on("response", on_resp)
        page.goto("https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        try:
            page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
            print("  clicked a Search button")
        except Exception as exc:
            print(f"  could not find/click a Search button: {exc}")
        page.wait_for_timeout(WAIT_MS)
        for url, status, body in ajax_bodies:
            print(f"  [{status}] {url}\n    body[:1500]: {body!r}")
        if not ajax_bodies:
            print("  no jobsearch.ajax/searchjobs responses captured")
        ctx.close()

        # --- Kramer Levin: check if rendered jobs are embedded in raw response ---
        section("Kramer Levin -- checking if job data is server-embedded")
        ctx = browser.new_context(user_agent=UA)
        resp = ctx.request.get("https://careers.hsfkramer.com/global/en/us/search-results")
        raw = resp.text()
        print(f"  'Help Desk Technician' present in raw (pre-JS) HTML: {'Help Desk Technician' in raw}")
        print(f"  'New York, New York' present in raw HTML: {'New York, New York' in raw}")
        ctx.close()

        # --- Duane Morris: follow the real Support Staff Opportunities link ---
        section("Duane Morris -- following the Support Staff Opportunities link")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.duanemorris.com/site/careers.html", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        link = page.get_by_text("Support Staff Opportunities", exact=False).first
        href = link.get_attribute("href")
        print(f"  href of 'Support Staff Opportunities' link: {href!r}")
        if href:
            full_url = href if href.startswith("http") else f"https://www.duanemorris.com{href}"
            page.goto(full_url, wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  navigated to {full_url}")
            print(f"  page title: {page.title()!r}")
            print(f"  body text[:1000]: {page.inner_text('body')[:1000]!r}")
        ctx.close()

        # --- Crowell & Moring: follow the Professional Staff link ---
        section("Crowell & Moring -- following the Professional Staff link")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.crowell.com/en/careers", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        link = page.get_by_text("Professional Staff", exact=False).first
        href = link.get_attribute("href")
        print(f"  href of 'Professional Staff' link: {href!r}")
        if href:
            full_url = href if href.startswith("http") else f"https://www.crowell.com{href}"
            page.goto(full_url, wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  navigated to {full_url}")
            print(f"  page title: {page.title()!r}")
            print(f"  body text[:1000]: {page.inner_text('body')[:1000]!r}")
        ctx.close()

        # --- Ropes & Gray: hunt for the real careers URL from the homepage nav ---
        section("Ropes & Gray -- hunting for the real careers URL")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.ropesgray.com/en", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        career_links = page.eval_on_selector_all(
            "a", "els => els.filter(e => /career/i.test(e.href) || /career/i.test(e.textContent)).map(e => [e.textContent.trim(), e.href])"
        )
        print(f"  career-related links found on homepage: {career_links[:15]}")
        ctx.close()

        # --- Vinson & Elkins: find a fresh Tag on the real careers page ---
        section("Vinson & Elkins -- hunting for a fresh viGlobal Tag")
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto("https://www.velaw.com/careers/business-professionals/", wait_until="load")
        page.wait_for_timeout(WAIT_MS)
        vi_links = page.eval_on_selector_all(
            "a", "els => els.filter(e => /viRecruitSelfApply|viglobal|velaw\\.com\\/careers/i.test(e.href)).map(e => [e.textContent.trim(), e.href])"
        )
        print(f"  viGlobal-related links found: {vi_links[:15]}")
        ctx.close()

        # --- Akin Gump: check if job data is embedded server-side ---
        section("Akin Gump -- checking if job data is server-embedded")
        ctx = browser.new_context(user_agent=UA)
        resp = ctx.request.get("https://jobs.silkroad.com/AkinGump/AkinGump")
        raw = resp.text()
        print(f"  'Litigation Practice Coordinator' present in raw (pre-JS) HTML: {'Litigation Practice Coordinator' in raw}")
        print(f"  'Billing Assistant' present in raw HTML: {'Billing Assistant' in raw}")
        script_json = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', raw, re.DOTALL)
        print(f"  <script type=\"application/json\"> blocks found: {len(script_json)}")
        for block in script_json[:2]:
            print(f"    {block[:300]!r}")
        ctx.close()

        browser.close()


if __name__ == "__main__":
    main()
