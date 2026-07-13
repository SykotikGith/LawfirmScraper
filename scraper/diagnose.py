"""Diagnostic round 3: confirm the full field shape of Akerman's real
UltiPro search API (JobBoardView/LoadSearchResults with body
{"opportunitySearch": {"Text": "", "PageNumber": N, "PageSize": 50}}) and
that pagination actually advances, before writing the real adapter.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
BASE = "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/b855fc7e-c6e0-90cc-b829-ddbebeb6f274"
URL = f"{BASE}/JobBoardView/LoadSearchResults"


def search(page_number: int, page_size: int = 50) -> dict:
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json, text/plain, */*"
    body = {"opportunitySearch": {"Text": "", "PageNumber": page_number, "PageSize": page_size}}
    resp = requests.post(URL, headers=headers, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    page1 = search(1)
    print(f"top-level keys: {sorted(page1.keys())}")
    print(f"totalCount: {page1.get('totalCount')}")
    opps = page1.get("opportunities", [])
    print(f"opportunities on page 1: {len(opps)}")

    print("\n=== full JSON of first opportunity ===")
    print(json.dumps(opps[0], indent=2) if opps else "(none)")

    print("\n=== title / requisition / location summary, first 10 ===")
    for opp in opps[:10]:
        locs = opp.get("Locations") or []
        loc_names = [loc.get("LocalizedDescription") for loc in locs]
        print(f"  {opp.get('Title')!r} | req={opp.get('RequisitionNumber')} | locations={loc_names} | Id={opp.get('Id')}")

    print("\n=== page 2 (confirming pagination advances) ===")
    page2 = search(2)
    opps2 = page2.get("opportunities", [])
    print(f"opportunities on page 2: {len(opps2)}")
    if opps2:
        print(f"first title on page 2: {opps2[0].get('Title')!r} (Id={opps2[0].get('Id')})")
    page1_ids = {o.get("Id") for o in opps}
    page2_ids = {o.get("Id") for o in opps2}
    print(f"overlap between page 1 and page 2 Ids: {len(page1_ids & page2_ids)}")


if __name__ == "__main__":
    main()
