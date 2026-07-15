"""Category 2 experimental pass -- per the original Playwright request,
these are the WAF/Cloudflare/Imperva-blocked firms to try with a real
headless browser as a second pass after Category 1 (now fully done).
Explicit instruction: don't force it if the challenge still blocks a
real browser, just report which succeed vs. which are genuinely stuck.

9 of these are iCIMS tenants blocked by AWS WAF's "Human Verification"
challenge (confirmed via plain HTTP in earlier research); Kirkland &
Ellis is a Cloudflare "Just a moment..." challenge; McDermott is an
Imperva Incapsula challenge. This navigates each with a real
headless-Chromium session and checks whether the challenge page still
shows, or whether real job content gets through.

Usage: python -m scraper.diagnose_browser
"""
from __future__ import annotations

import re

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
WAIT_MS = 5_000

CHALLENGE_SIGNATURES = [
    "just a moment", "attention required", "human verification",
    "access denied", "pardon our interruption", "checking your browser",
    "cf-browser-verification", "request unsuccessful", "incident id",
    "are you a robot", "verify you are a human", "sorry, you have been blocked",
]

FIRMS = [
    ("Orrick", "https://careers-orrick.icims.com/jobs/search?pr=0&in_iframe=1"),
    ("Milbank", "https://careers-milbank.icims.com/jobs/intro?hashed=-435594439"),
    ("Lewis Brisbois", "https://careers-lewisbrisbois.icims.com/jobs/search"),
    ("Gordon Rees", "https://careers-grsm.icims.com/jobs/search"),
    ("Foley & Lardner", "https://careers-foley.icims.com/jobs/intro?hashed=-626009846"),
    ("Nelson Mullins", "https://careers-nelsonmullins.icims.com/jobs/search"),
    ("Mayer Brown", "https://globalcareers-mayerbrown.icims.com/jobs/search?hashed=124489139"),
    ("Latham & Watkins", "https://careers-lw.icims.com/jobs/search?hashed=-625915638"),
    ("Willkie Farr & Gallagher", "https://jobs-willkie.icims.com/jobs/search?hashed=-625885970"),
    ("Kirkland & Ellis", "https://staffjobsus.kirkland.com/jobs/search/"),
    ("McDermott Will & Emery", "https://www.mcdermottlaw.com/careers"),
]


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

        def check(name: str, url: str):
            section(f"{name} -- {url}")
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            resp = page.goto(url, wait_until="load")
            page.wait_for_timeout(WAIT_MS)
            print(f"  status: {resp.status if resp else None}")
            print(f"  title: {page.title()!r}")
            body = page.inner_text("body")
            body_lower = body.lower()
            hit = next((sig for sig in CHALLENGE_SIGNATURES if sig in body_lower), None)
            if hit:
                print(f"  BLOCKED -- challenge signature found: {hit!r}")
            else:
                print("  no challenge signature found -- possible real content")
                job_count = len(re.findall(r"job|position|opening", body, re.I))
                print(f"  job/position/opening keyword count: {job_count}")
            print(f"  body text[:1000]: {body[:1000]!r}")
            ctx.close()

        for name, url in FIRMS:
            run_safely(name, lambda name=name, url=url: check(name, url))

        browser.close()


if __name__ == "__main__":
    main()
