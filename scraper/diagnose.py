"""Batch round 1: investigating 9 new firm leads at once (user supplied all
9 URLs in a single message). Two are near-zero-risk (standard old-style
Workday subdomains, and an Oracle Recruiting Cloud site matching a pattern
already confirmed working for another firm) -- those just need a live
sanity check of real data before being wired in. The other six are on ATS
platforms this project hasn't touched yet (ADP myjobs, Taleo Business
Edition, Taleo Enterprise careersection, CV-Mail UK, FloRecruit, and a
viGlobal deployment hosted on the firm's own domain rather than
viglobalcloud.com) -- those need first-pass structural inspection to see
if there's a JSON API or a scrapeable server-rendered table before any
adapter work starts.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def fetch(url: str, method: str = "GET", **kwargs) -> requests.Response | None:
    try:
        if method == "GET":
            return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
        return requests.post(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return None


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# --- 1. Skadden Arps (Workday, old-style) -------------------------------
def check_skadden() -> None:
    section("Skadden Arps -- Workday CXS, tenant=skadden wd=wd5 site=Skadden_Careers")
    prime = fetch("https://skadden.wd5.myworkdayjobs.com/Skadden_Careers")
    if prime:
        print(f"  prime GET: status={prime.status_code} len={len(prime.text)}")
    api_url = "https://skadden.wd5.myworkdayjobs.com/wday/cxs/skadden/Skadden_Careers/jobs"
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    resp = fetch(api_url, method="POST", json=body)
    if resp is None:
        return
    print(f"  CXS POST: status={resp.status_code} len={len(resp.text)}")
    if resp.status_code == 200:
        data = resp.json()
        postings = data.get("jobPostings", [])
        print(f"  total={data.get('total')} returned={len(postings)}")
        for job in postings[:10]:
            print(f"    - {job.get('title')!r} | {job.get('locationsText')!r}")


# --- 2. Sidley Austin (Workday, old-style) ------------------------------
def check_sidley() -> None:
    section("Sidley Austin -- Workday CXS, tenant=sidley wd=wd501 site=US")
    prime = fetch("https://sidley.wd501.myworkdayjobs.com/en-US/US")
    if prime:
        print(f"  prime GET: status={prime.status_code} len={len(prime.text)}")
    api_url = "https://sidley.wd501.myworkdayjobs.com/wday/cxs/sidley/US/jobs"
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
    resp = fetch(api_url, method="POST", json=body)
    if resp is None:
        return
    print(f"  CXS POST: status={resp.status_code} len={len(resp.text)}")
    if resp.status_code == 200:
        data = resp.json()
        postings = data.get("jobPostings", [])
        print(f"  total={data.get('total')} returned={len(postings)}")
        for job in postings[:10]:
            print(f"    - {job.get('title')!r} | {job.get('locationsText')!r}")


# --- 3. Proskauer Rose (Oracle Recruiting Cloud) ------------------------
def check_proskauer() -> None:
    section("Proskauer Rose -- Oracle Recruiting Cloud, host=dfa.fa.us1.oraclecloud.com siteNumber=CX_1001")
    api_url = (
        "https://dfa.fa.us1.oraclecloud.com/hcmRestApi/resources/latest/"
        "recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
        "&finder=findReqs;siteNumber=CX_1001,limit=100"
    )
    resp = fetch(api_url)
    if resp is None:
        return
    print(f"  status={resp.status_code} len={len(resp.text)}")
    if resp.status_code == 200:
        try:
            data = resp.json()
        except ValueError:
            print(f"  NOT JSON, body[:300]: {resp.text[:300]!r}")
            return
        items = data.get("items", [{}])
        reqs = items[0].get("requisitionList", []) if items else []
        print(f"  requisitions returned: {len(reqs)}")
        for req in reqs[:10]:
            print(f"    - {req.get('Title')!r} | {req.get('PrimaryLocation')!r}")


# --- 4. Vinson & Elkins (viGlobal, self-hosted domain) ------------------
def check_vinson_elkins() -> None:
    section("Vinson & Elkins -- viGlobal on portal.velaw.com (self-hosted, not viglobalcloud.com)")
    url = (
        "https://portal.velaw.com/viDesktopEx/viRecruitSelfApply/ReDefault.aspx"
        "?Tag=bf5353fd-6c9b-41e3-a72f-7abd61690415"
    )
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    has_table = "contentPlaceHolder_gridviewList" in resp.text
    print(f"  contains contentPlaceHolder_gridviewList table id: {has_table}")
    if not has_table:
        other_tables = re.findall(r'<table[^>]*id="([^"]+)"', resp.text)
        print(f"  other table ids found: {other_tables[:10]}")
        print(f"  body[:500]: {resp.text[:500]!r}")


# --- 5. Venable (ADP myjobs) ---------------------------------------------
def check_venable() -> None:
    section("Venable -- ADP myjobs (new platform, unresearched)")
    url = "https://myjobs.adp.com/venablebusinessprofessionalcareers/cx"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    api_hints = re.findall(r'["\'](?:https?:)?//[^"\']*adp\.com[^"\']*api[^"\']*["\']', resp.text, re.I)
    print(f"  adp.com api-looking URLs found: {sorted(set(api_hints))[:10]}")
    script_srcs = re.findall(r'<script[^>]+src="([^"]+)"', resp.text)
    print(f"  script src count: {len(script_srcs)}; sample: {script_srcs[:5]}")
    print(f"  body[:500]: {resp.text[:500]!r}")


# --- 6. Sullivan & Cromwell (Taleo Business Edition) ---------------------
def check_sullivan_cromwell() -> None:
    section("Sullivan & Cromwell -- Taleo Business Edition (phg.tbe.taleo.net)")
    url = "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=SULLCROM&cws=38"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    print(f"  content-type: {resp.headers.get('Content-Type')}")
    job_link_hints = re.findall(r'href="([^"]*jobdetail[^"]*)"', resp.text, re.I)
    print(f"  jobdetail links found: {len(job_link_hints)}; sample: {job_link_hints[:5]}")
    print(f"  body[:500]: {resp.text[:500]!r}")


# --- 7. Squire Patton Boggs (CV-Mail UK) ---------------------------------
def check_squire_patton_boggs() -> None:
    section("Squire Patton Boggs -- CV-Mail UK (fsr.cvmailuk.com, ColdFusion)")
    url = (
        "https://fsr.cvmailuk.com/spb/main.cfm?page=jobBoard&rcd=1309578"
        "&srxksl=1&groupType_21=5039&filter="
    )
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    print(f"  body[:500]: {resp.text[:500]!r}")


# --- 8. Sheppard Mullin (FloRecruit) -------------------------------------
def check_sheppard_mullin() -> None:
    section("Sheppard Mullin -- FloRecruit (florecruit.com, new platform)")
    url = "https://florecruit.com/v2/app/sheppardbusinessservices/jobs"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    api_hints = re.findall(r'["\'](?:https?:)?//[^"\']*florecruit[^"\']*["\']', resp.text, re.I)
    print(f"  florecruit-domain URLs found in body: {sorted(set(api_hints))[:10]}")
    print(f"  body[:500]: {resp.text[:500]!r}")


# --- 9. Paul Weiss (Taleo Enterprise careersection) -----------------------
def check_paul_weiss() -> None:
    section("Paul Weiss -- Taleo Enterprise careersection (paulweiss.taleo.net)")
    url = "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl"
    resp = fetch(url)
    if resp is None:
        return
    print(f"  status={resp.status_code} final_url={resp.url} len={len(resp.text)}")
    rest_hints = re.findall(r'["\'](/careersection/rest/[^"\']+)["\']', resp.text)
    print(f"  /careersection/rest/ paths found: {sorted(set(rest_hints))[:10]}")
    print(f"  body[:500]: {resp.text[:500]!r}")


def main() -> None:
    check_skadden()
    check_sidley()
    check_proskauer()
    check_vinson_elkins()
    check_venable()
    check_sullivan_cromwell()
    check_squire_patton_boggs()
    check_sheppard_mullin()
    check_paul_weiss()


if __name__ == "__main__":
    main()
