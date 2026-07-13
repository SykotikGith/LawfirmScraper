"""Diagnostic: 6 firms confirmed to have a real Workday tenant (via
ats_probe.py's path-specific-error signal) show NO Workday link in any
format on their careers pages, even after find_workday_sites.py's regex
was fixed to also catch the myworkdaysite.com front-end shape. Same
pattern as Debevoise & Plimpton / O'Melveny & Myers / Milbank earlier in
this project: a real-but-dormant/internal Workday tenant, with the actual
external-recruiting ATS being a different platform entirely.

This scans each firm's careers page for ANY known ATS platform domain
(not just Workday) -- iCIMS, Greenhouse, Oracle Recruiting Cloud,
ApplicantStack, HRMdirect, viGlobal, Circa Works, PageUp/eArcu, UltiPro,
plus a few not yet seen in this project (Phenom, SmartRecruiters, Taleo,
SuccessFactors, Avature, Jobvite, Lever, BambooHR) -- and prints the final
URL after redirects (in case a client-side/meta redirect points somewhere
the raw body text doesn't mention), so the real platform can be
identified in one pass instead of guessing again.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

# (firm, url to check -- the best-content path found by find_workday_sites.py)
FIRMS = [
    ("McDermott Will & Emery", "https://www.mwe.com/careers"),
    ("Morrison & Foerster", "https://www.mofo.com/careers"),
    ("Skadden Arps", "https://www.skadden.com/careers"),
    ("Davis Polk", "https://www.davispolk.com"),  # /careers 403'd, try bare domain
    ("Hogan Lovells", "https://www.hoganlovells.com"),  # /careers 404'd, try bare domain
    ("Cleary Gottlieb", "https://www.clearygottlieb.com/careers"),
]

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
    "Phenom": r"phenompeople\.com",
    "SmartRecruiters": r"smartrecruiters\.com",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors\.com",
    "Avature": r"avature\.net",
    "Jobvite": r"jobvite\.com",
    "Lever": r"jobs\.lever\.co",
    "BambooHR": r"bamboohr\.com",
    "Workday (any format)": r"myworkday(?:jobs|site)\.com",
}


def scan(firm: str, url: str) -> None:
    print(f"\n=== {firm} -- {url} ===")
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return

    print(f"  status={resp.status_code}  final_url={resp.url}  len={len(resp.text)}")

    text = resp.text
    found_any = False
    for label, pattern in ATS_DOMAIN_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found_any = True
            count = len(re.findall(pattern, text, re.IGNORECASE))
            idx = match.start()
            print(f"  FOUND {label}: {count}x, context: ...{text[max(0, idx - 80):idx + 120]}...")

    meta_refresh = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]*content=["\']([^"\']+)["\']', text, re.IGNORECASE
    )
    if meta_refresh:
        print(f"  META REFRESH found: {meta_refresh.group(1)}")

    if not found_any:
        print("  No known ATS domain found. First 500 chars of body:")
        print(f"  {text[:500]!r}")


def main() -> None:
    for firm, url in FIRMS:
        scan(firm, url)


if __name__ == "__main__":
    main()
