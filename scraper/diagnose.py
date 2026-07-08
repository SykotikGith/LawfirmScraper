"""Round 2 diagnostic: targeted follow-ups on the firms that returned a real
200 response but zero parsed postings, or truncated pagination, on the
first live run. Round 1 already resolved iCIMS (blocked by AWS WAF -- not
fixable here) and Perkins Coie (wrong Workday pod, now fixed to wd115).

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20

ATS_HINTS = [
    "icims", "workday", "myworkdayjobs", "greenhouse.io", "lever.co",
    "smartrecruiters", "ultipro", "ukg", "dayforce", "paycor",
    "applicantstack", "clearcompany", "hrmdirect", "jazzhr", "bamboohr",
    "successfactors", "taleo", "oraclecloud", "avature", "phenompeople",
    "adp.com", "pageuppeople",
]


def snippet_around(text: str, needle: str, radius: int = 150) -> str:
    idx = text.lower().find(needle.lower())
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(needle) + radius)
    return text[start:end].replace("\n", " ")


def cozen_oconnor() -> None:
    print("\n=== Cozen O'Connor: locating the job list key ===")
    url = (
        "https://hctq.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
        "recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,limit=100"
    )
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    data = resp.json()
    print("top-level keys:", list(data.keys()))
    items = data.get("items", [])
    print(f"items: len={len(items)}")
    if items:
        print("items[0] keys:", list(items[0].keys()))
        for key, val in items[0].items():
            if isinstance(val, list):
                print(f"  items[0][{key!r}] is a list of length {len(val)}")
                if val:
                    print(f"    first element keys: {list(val[0].keys()) if isinstance(val[0], dict) else val[0]}")


def reed_smith() -> None:
    print("\n=== Reed Smith: locating job link pattern ===")
    url = "https://careers.reedsmith.com/jobs/vacancy/find/results"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    print(f"'JobOpeningId' occurrences: {text.count('JobOpeningId')}")
    print(f"'vacancy' occurrences: {text.count('vacancy')}")
    hrefs = re.findall(r'href="([^"]+)"', text)
    vacancy_hrefs = [h for h in hrefs if "vacanc" in h.lower() or "job" in h.lower()]
    print(f"hrefs containing 'vacanc'/'job' (first 10 of {len(vacancy_hrefs)}):")
    for h in vacancy_hrefs[:10]:
        print(" ", h)


def fisher_phillips() -> None:
    print("\n=== Fisher Phillips: locating job link pattern ===")
    url = "https://fisherphillips.hrmdirect.com/employment/job-openings.php"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    print(f"'req=' occurrences: {text.count('req=')}")
    hrefs = re.findall(r'href="([^"]+)"', text)
    job_hrefs = [h for h in hrefs if "req=" in h or "job-opening" in h or "view.php" in h]
    print(f"hrefs containing 'req='/'job-opening'/'view.php' (first 10 of {len(job_hrefs)}):")
    for h in job_hrefs[:10]:
        print(" ", h)


def marshall_dennehey() -> None:
    print("\n=== Marshall Dennehey: looking for an embedded ATS widget ===")
    url = "https://www.marshalldennehey.com/careers"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text
    for hint in ATS_HINTS:
        if hint in text.lower():
            print(f"  found hint '{hint}':")
            print("   ", snippet_around(text, hint))
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', text)
    print(f"iframes found: {iframes}")
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', text)
    external_scripts = [s for s in scripts if s.startswith("http") and "marshalldennehey" not in s]
    print(f"external scripts (first 15): {external_scripts[:15]}")


def workday_pagination_trace(label: str, tenant: str, wd: str, site: str) -> None:
    print(f"\n=== {label}: pagination trace ===")
    api_url = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    offset = 0
    limit = 20
    for page in range(6):
        body = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        resp = requests.post(api_url, headers=DEFAULT_HEADERS, json=body, timeout=TIMEOUT)
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"  offset={offset}: status={resp.status_code} non-JSON body: {resp.text[:200]}")
            break
        n = len(data.get("jobPostings", []))
        total = data.get("total")
        print(f"  offset={offset}: status={resp.status_code} total={total} jobPostings_returned={n}")
        if n == 0:
            break
        offset += limit


def main() -> None:
    cozen_oconnor()
    reed_smith()
    fisher_phillips()
    marshall_dennehey()
    workday_pagination_trace("DLA Piper", "dlapiper", "wd1", "dlapiper")
    workday_pagination_trace("Clyde & Co US", "clydeco", "wd103", "clydecocareers")


if __name__ == "__main__":
    main()
