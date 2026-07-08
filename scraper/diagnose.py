"""Diagnostic: verify/refute the Goodwin Procter (Greenhouse "goodwin") and
Ropes & Gray (ApplicantStack "ropesgray") guesses by checking their real
official sites for an embedded ATS link, the same way Wilson Elser's real
Greenhouse token was found in its React bundle. Also a quick sanity check
that winstontaylor.com is genuinely an unrelated company (confirming the
Winston & Strawn/HRMdirect "winston" collision is a real rejection, not a
mistake).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

ATS_HINTS = [
    "greenhouse.io", "myworkdayjobs.com", "icims.com", "applicantstack.com",
    "hrmdirect.com", "avature.net", "phenompeople.com", "oraclecloud.com",
    "smartrecruiters.com", "lever.co", "ultipro.com", "successfactors.com",
    "taleo.net", "pageuppeople.com",
]


def sniff_ats(label: str, url: str) -> None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        print(f"\n{label}: {url}")
        print(f"  status={resp.status_code} len={len(resp.text)}")
        text = resp.text
        found_any = False
        for hint in ATS_HINTS:
            if hint in text.lower():
                found_any = True
                idx = text.lower().find(hint)
                snippet = text[max(0, idx - 80):idx + 100].replace("\n", " ")
                print(f"  found '{hint}': {snippet}")
        if not found_any:
            print("  no known ATS hint found in this page's raw HTML")
            # Check for referenced JS bundles, in case it's client-rendered
            # like Wilson Elser was.
            js_paths = re.findall(r'src="([^"]+\.js[^"]*)"', text)
            same_origin_js = [j for j in js_paths if j.startswith("/") or url.split("/")[2] in j]
            print(f"  {len(same_origin_js)} same-origin JS bundle(s) referenced "
                  f"(check these by hand if nothing else here helps): {same_origin_js[:5]}")
    except requests.exceptions.RequestException as exc:
        print(f"\n{label}: {url}\n  EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== Winston Taylor sanity check (confirm unrelated to Winston & Strawn) ===")
    sniff_ats("Winston Taylor", "https://www.winstontaylor.com/")

    print("\n=== Goodwin Procter: hunting for the real Greenhouse token (or other ATS) ===")
    for path in ["/en", "/en/careers", "/en/careers/opportunities", "/careers"]:
        sniff_ats("Goodwin Procter", f"https://www.goodwinlaw.com{path}")

    print("\n=== Ropes & Gray: hunting for the real ApplicantStack tenant (or other ATS) ===")
    for path in ["/en", "/en/careers", "/en/careers/professional-staff-careers", "/careers"]:
        sniff_ats("Ropes & Gray", f"https://www.ropesgray.com{path}")


if __name__ == "__main__":
    main()
