"""Playwright-based diagnostic: loads each Category 1 firm's real page in a
headless browser and captures every network response that looks like a
real job-listing API call (JSON content-type, or a URL containing a
job/career/search/api-ish keyword), plus a snippet of the final rendered
DOM as a fallback signal for firms where no clean API call turns up.

Category 1 = firms believed to be blocked by client-side JS rendering
rather than active bot-detection, so a real headless browser should just
work: Akin Gump, Sheppard Mullin, Venable, Paul Weiss, Kramer Levin (HSF
Kramer), Duane Morris, Crowell & Moring, Dentons, Ropes & Gray, and
Vinson & Elkins (already a working FIRMS entry via viGlobal, but
intermittently returns zero postings on scheduled runs -- included here
to see whether a real browser session behaves more reliably than a bare
GET, since that's a plausible fix for a session/cookie issue).

SETUP (this needs Playwright + a real Chromium binary, not just the
requests/bs4 stack used by diagnose.py):
    pip install playwright
    playwright install chromium

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

JOB_URL_HINT_RE = re.compile(r"(job|career|search|position|opening|api|graphql)", re.I)
NAV_TIMEOUT_MS = 30_000
POST_LOAD_WAIT_MS = 4_000


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def capture(label: str, url: str, click_text: str | None = None) -> None:
    section(f"{label} -- {url}")
    candidates: list[tuple[str, int, str, str]] = []  # url, status, content_type, body_snippet

    def on_response(resp):
        try:
            ct = resp.headers.get("content-type", "")
            is_json = "json" in ct.lower()
            url_hints = JOB_URL_HINT_RE.search(resp.url)
            if not (is_json or url_hints):
                return
            # Skip obvious noise (analytics, fonts, tracking pixels) even if url matches.
            if any(noise in resp.url.lower() for noise in ["gtm.js", "analytics", "googletagmanager", ".woff", ".css", ".png", ".jpg", ".svg"]):
                return
            body_snippet = ""
            if is_json:
                try:
                    body_snippet = resp.text()[:500]
                except Exception:
                    body_snippet = "(body unavailable)"
            candidates.append((resp.url, resp.status, ct, body_snippet))
        except Exception as exc:  # noqa: BLE001 - diagnostic script, never crash the run
            print(f"  [response handler error, ignored]: {exc}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=UA)
            page = context.new_page()
            page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            page.on("response", on_response)

            page.goto(url, wait_until="load")
            page.wait_for_timeout(POST_LOAD_WAIT_MS)

            if click_text:
                try:
                    page.get_by_text(click_text, exact=False).first.click(timeout=5000)
                    page.wait_for_timeout(POST_LOAD_WAIT_MS)
                    print(f"  clicked element matching text {click_text!r}")
                except Exception as exc:
                    print(f"  could not click {click_text!r}: {exc}")

            title = page.title()
            body_text = page.inner_text("body")
            browser.close()
    except Exception as exc:  # noqa: BLE001
        print(f"  EXCEPTION during page load: {type(exc).__name__}: {exc}")
        return

    print(f"  page title: {title!r}")
    print(f"  candidate API-looking responses captured: {len(candidates)}")
    seen_urls = set()
    for resp_url, status, ct, body in candidates:
        if resp_url in seen_urls:
            continue
        seen_urls.add(resp_url)
        print(f"    [{status}] {ct} {resp_url}")
        if body:
            print(f"      body[:500]: {body!r}")

    print(f"\n  rendered body text[:800]: {body_text[:800]!r}")


def main() -> None:
    capture("Akin Gump", "https://jobs.silkroad.com/AkinGump/AkinGump")
    capture("Sheppard Mullin", "https://florecruit.com/v2/app/sheppardbusinessservices/jobs")
    capture("Venable", "https://myjobs.adp.com/venablebusinessprofessionalcareers/cx")
    capture("Paul Weiss", "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl")
    capture("Kramer Levin (HSF Kramer)", "https://careers.hsfkramer.com/global/en/us/search-results")
    capture("Duane Morris", "https://www.duanemorris.com/site/careers.html", click_text="Support Staff")
    capture("Crowell & Moring", "https://www.crowell.com/en/careers")
    capture("Dentons", "https://www.dentons.com/en/careers/careers-in-the-united-states/business-services-in-the-united-states/")
    capture("Ropes & Gray (main site)", "https://www.ropesgray.com/en/careers")
    capture("Ropes & Gray (ApplicantStack tenant)", "https://ropesgray.applicantstack.com/x/openings")
    capture(
        "Vinson & Elkins (checking session/cookie reliability)",
        "https://portal.velaw.com/viDesktopEx/viRecruitSelfApply/ReDefault.aspx?Tag=bf5353fd-6c9b-41e3-a72f-7abd61690415",
    )


if __name__ == "__main__":
    main()
