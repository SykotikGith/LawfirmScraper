"""AmLaw 100 batch, round 5: final follow-up on the 4 live leads from
round 4 before the rest get documented as manual-check.

K&L Gates: found a real "All Current Openings" link to /job-opportunities
on the careers landing page -- fetch it directly and scan for a known ATS
platform, and dump its raw structure if nothing matches.

Crowell & Moring: found an "Apply Now" link, but it may be a specific
track's form rather than the general listing -- fetch it and also try
the parent /en/careers/ page for a broader listing link.

Dentons: sitemap already had real individual job posting URLs indexed
directly (e.g. .../business-services-in-the-united-states/2026/july/
legal-administrative-assistant-newyork), and the category landing page
shows Angular markers -- checking whether the category page itself has
real job links in server-rendered HTML despite the Angular framework
(Angular SSR/prerendering for SEO is common), since the sitemap proves
the individual pages exist and are indexed either way.

Sheppard Mullin: Next.js framework detected -- checking for a
__NEXT_DATA__ script block, which Next.js commonly embeds server-side for
hydration and often contains real page data even in an otherwise
client-rendered app (confirmed absent or present decides whether this is
scrapable without a headless browser).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

ATS_DOMAIN_PATTERNS = {
    "iCIMS": r"icims\.com",
    "Greenhouse": r"greenhouse\.io",
    "Oracle Recruiting Cloud": r"oraclecloud\.com",
    "ApplicantStack": r"applicantstack\.com",
    "HRMdirect": r"hrmdirect\.com",
    "viGlobal": r"viglobalcloud\.com",
    "Circa Works": r"circaworks\.com",
    "PageUp/eArcu": r"\bearcu\b",
    "UltiPro": r"ultipro\.com",
    "Jobvite": r"jobvite\.com",
    "Phenom": r"phenompeople\.com",
    "SmartRecruiters": r"smartrecruiters\.com",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors\.com",
    "Avature": r"avature\.net",
    "Lever": r"jobs\.lever\.co",
    "BambooHR": r"bamboohr\.com",
    "Workday (any format)": r"myworkday(?:jobs|site)\.com",
}


def fetch(url: str) -> requests.Response | None:
    try:
        return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION fetching {url}: {type(exc).__name__}: {exc}")
        return None


def scan_ats(text: str) -> str | None:
    for label, pattern in ATS_DOMAIN_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None


def check_klgates() -> None:
    print("=== K&L Gates: /job-opportunities ===")
    resp = fetch("https://www.klgates.com/job-opportunities")
    if resp is None or resp.status_code != 200:
        print(f"  status={resp.status_code if resp else None}")
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    ats = scan_ats(resp.text)
    print(f"  ATS found: {ats}")
    if not ats:
        soup = BeautifulSoup(resp.text, "lxml")
        links = [a.get("href") for a in soup.find_all("a", href=True)][:30]
        print(f"  first 30 links on page: {links}")
        print(f"  first 800 chars: {resp.text[:800]!r}")


def check_crowell() -> None:
    print("\n=== Crowell & Moring: careers landing + apply-now ===")
    for url in ["https://www.crowell.com/en/careers", "https://www.crowell.com/en/careers/experienced-lawyers/apply-now"]:
        resp = fetch(url)
        if resp is None or resp.status_code != 200:
            print(f"  {url}: status={resp.status_code if resp else None}")
            continue
        print(f"  {url}: status={resp.status_code} len={len(resp.text)}")
        ats = scan_ats(resp.text)
        print(f"    ATS found: {ats}")
        soup = BeautifulSoup(resp.text, "lxml")
        openings_links = [
            (a.get_text(strip=True), a.get("href"))
            for a in soup.find_all("a", href=True)
            if re.search(r"open|position|search|listing|business.profession", a.get_text(strip=True), re.IGNORECASE)
        ]
        print(f"    candidate links: {openings_links[:10]}")


def check_dentons() -> None:
    print("\n=== Dentons: category landing page raw structure ===")
    url = "https://www.dentons.com/en/careers/careers-in-the-united-states/business-services-in-the-united-states/"
    resp = fetch(url)
    if resp is None or resp.status_code != 200:
        print(f"  status={resp.status_code if resp else None}")
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    soup = BeautifulSoup(resp.text, "lxml")
    job_links = [a.get("href") for a in soup.find_all("a", href=True) if "/careers/" in a.get("href", "") and re.search(r"/20\d\d/", a.get("href", ""))]
    print(f"  job-posting-shaped links found in static HTML: {len(job_links)}")
    for link in job_links[:15]:
        print(f"    {link}")
    if not job_links:
        print(f"  first 1000 chars: {resp.text[:1000]!r}")


def check_sheppard_mullin() -> None:
    print("\n=== Sheppard Mullin: __NEXT_DATA__ check ===")
    resp = fetch("https://www.sheppard.com/careers")
    if resp is None or resp.status_code != 200:
        print(f"  status={resp.status_code if resp else None}")
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if match:
        print(f"  __NEXT_DATA__ found, length={len(match.group(1))}")
        print(f"  first 1500 chars: {match.group(1)[:1500]}")
    else:
        print("  no __NEXT_DATA__ block found")
        print(f"  first 800 chars: {resp.text[:800]!r}")


def main() -> None:
    check_klgates()
    check_crowell()
    check_dentons()
    check_sheppard_mullin()


if __name__ == "__main__":
    main()
