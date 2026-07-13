"""Diagnostic round 4: LoadSearchResults ignored PageSize (always returned
20) and PageNumber=2 returned the identical 20 results as PageNumber=1 --
pagination isn't working the way it was guessed. This tries several
alternate parameter shapes to find the one that actually changes the
result set / count, before writing the real adapter.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
BASE = "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/b855fc7e-c6e0-90cc-b829-ddbebeb6f274"
URL = f"{BASE}/JobBoardView/LoadSearchResults"

FIRST_KNOWN_ID = "4b4e8273-7c45-4a32-b928-56dd69e6b2be"  # Legal Administrative Assistant, always page-1 item 1


def post(body: dict) -> dict:
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json, text/plain, */*"
    resp = requests.post(URL, headers=headers, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def summarize(label: str, body: dict) -> None:
    try:
        data = post(body)
    except Exception as exc:  # noqa: BLE001
        print(f"{label}: EXCEPTION {type(exc).__name__}: {exc}")
        return
    opps = data.get("opportunities", [])
    ids = [o.get("Id") for o in opps]
    first_title = opps[0].get("Title") if opps else None
    same_as_page1 = ids and ids[0] == FIRST_KNOWN_ID
    print(f"{label}: count={len(opps)} totalCount={data.get('totalCount')} "
          f"first_title={first_title!r} same_first_item_as_default_page1={same_as_page1}")


def main() -> None:
    print("--- baseline: no paging fields at all ---")
    summarize("no-paging", {"opportunitySearch": {"Text": ""}})

    print("\n--- PageSize variants (is 20 a hard cap or did the field name miss?) ---")
    summarize("PageSize=5", {"opportunitySearch": {"Text": "", "PageSize": 5}})
    summarize("PageSize=100", {"opportunitySearch": {"Text": "", "PageSize": 100}})
    summarize("Take=100", {"opportunitySearch": {"Text": "", "Take": 100}})

    print("\n--- PageNumber variants (0-based vs 1-based vs alternate names) ---")
    summarize("PageNumber=0", {"opportunitySearch": {"Text": "", "PageNumber": 0, "PageSize": 20}})
    summarize("PageNumber=1", {"opportunitySearch": {"Text": "", "PageNumber": 1, "PageSize": 20}})
    summarize("PageNumber=2", {"opportunitySearch": {"Text": "", "PageNumber": 2, "PageSize": 20}})
    summarize("PageIndex=1", {"opportunitySearch": {"Text": "", "PageIndex": 1, "PageSize": 20}})
    summarize("Page=2", {"opportunitySearch": {"Text": "", "Page": 2, "PageSize": 20}})
    summarize("Skip=20,Take=20", {"opportunitySearch": {"Text": "", "Skip": 20, "Take": 20}})
    summarize(
        "nested Paging object",
        {"opportunitySearch": {"Text": "", "Paging": {"PageNumber": 2, "PageSize": 20}}},
    )
    summarize(
        "PageNumber+PageSize outside opportunitySearch",
        {"opportunitySearch": {"Text": ""}, "PageNumber": 2, "PageSize": 20},
    )


if __name__ == "__main__":
    main()
