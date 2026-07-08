"""One-shot diagnostic: probe the endpoints that failed or returned zero
postings on the last real run, and print enough raw detail (status code,
content-type, body snippet) to fix the adapters without guessing blind.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def show(label: str, resp: requests.Response, body_chars: int = 800) -> None:
    print(f"\n--- {label} ---")
    print(f"status={resp.status_code} content-type={resp.headers.get('content-type')} "
          f"final_url={resp.url}")
    body = resp.text
    print(body[:body_chars].replace("\n", " ")[:body_chars])
    if len(body) > body_chars:
        print(f"...[{len(body)} chars total]")


def probe_get(label: str, url: str, **kwargs) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
        show(label, resp)
        return resp
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- {label} ---\nEXCEPTION: {type(exc).__name__}: {exc}")
        return None


def probe_post(label: str, url: str, body: dict) -> requests.Response | None:
    try:
        resp = requests.post(url, headers=DEFAULT_HEADERS, json=body, timeout=TIMEOUT)
        show(label, resp)
        return resp
    except Exception as exc:  # noqa: BLE001
        print(f"\n--- {label} ---\nEXCEPTION: {type(exc).__name__}: {exc}")
        return None


def main() -> None:
    # --- iCIMS: 405 on /jobs/search?pr=0&in_iframe=1 for all 3 tenants ---
    for tenant in ["lewisbrisbois", "grsm", "orrick"]:
        probe_get(f"iCIMS {tenant} /jobs/intro", f"https://careers-{tenant}.icims.com/jobs/intro")
        probe_get(
            f"iCIMS {tenant} /jobs/search?ss=1",
            f"https://careers-{tenant}.icims.com/jobs/search?ss=1&searchRelation=keyword_all",
        )

    # --- Cozen O'Connor: 200 but 0 postings parsed ---
    probe_get(
        "Cozen O'Connor ORC api_url (current config)",
        "https://hctq.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
        "recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1,limit=100",
    )
    probe_get(
        "Cozen O'Connor ORC candidate experience page",
        "https://hctq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/",
    )

    # --- Reed Smith: 0 postings ---
    probe_get(
        "Reed Smith careers.reedsmith.com results page",
        "https://careers.reedsmith.com/jobs/vacancy/find/results",
    )
    probe_get("Reed Smith careers.reedsmith.com home", "https://careers.reedsmith.com/jobs/home/")

    # --- Fisher Phillips: 0 postings ---
    probe_get(
        "Fisher Phillips hrmdirect job-openings.php",
        "https://fisherphillips.hrmdirect.com/employment/job-openings.php",
    )

    # --- Marshall Dennehey: 404 ---
    for path in ["/careers", "/careers/", "/careers/current-openings", "/careers/attorneys"]:
        probe_get(f"Marshall Dennehey {path}", f"https://www.marshalldennehey.com{path}")

    # --- Perkins Coie: Workday 422 ---
    probe_get(
        "Perkins Coie Workday HTML careers page",
        "https://perkinscoie.wd1.myworkdayjobs.com/perkinscoieexternal",
    )
    for wd in ["wd1", "wd115", "wd5"]:
        probe_post(
            f"Perkins Coie Workday API ({wd})",
            f"https://perkinscoie.{wd}.myworkdayjobs.com/wday/cxs/perkinscoie/perkinscoieexternal/jobs",
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        )

    # --- Sanity check: Workday firms that already work, to confirm pagination is complete ---
    for label, tenant, wd, site in [
        ("DLA Piper", "dlapiper", "wd1", "dlapiper"),
        ("Clyde & Co US", "clydeco", "wd103", "clydecocareers"),
    ]:
        resp = probe_post(
            f"{label} Workday total-count check",
            f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
            {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""},
        )
        if resp is not None and resp.status_code == 200:
            try:
                print(f"    -> reported total: {resp.json().get('total')}")
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    main()
