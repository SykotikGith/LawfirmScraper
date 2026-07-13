"""Diagnostic round 5: Skip/Take is the real pagination scheme for
Akerman's UltiPro search API. Confirm whether Take actually controls page
size (or 20 is hard-capped regardless), and sweep Skip across all 96
postings to confirm every one is retrieved exactly once (no gaps, no
duplicates) before writing the real adapter.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
BASE = "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/b855fc7e-c6e0-90cc-b829-ddbebeb6f274"
URL = f"{BASE}/JobBoardView/LoadSearchResults"


def search(skip: int, take: int) -> dict:
    headers = dict(DEFAULT_HEADERS)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json, text/plain, */*"
    body = {"opportunitySearch": {"Text": "", "Skip": skip, "Take": take}}
    resp = requests.post(URL, headers=headers, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    print("--- does Take control page size? ---")
    for take in (5, 10, 20, 50):
        data = search(0, take)
        print(f"  Take={take}: got {len(data.get('opportunities', []))} (totalCount={data.get('totalCount')})")

    print("\n--- sweeping Skip across all postings with Take=20 ---")
    all_ids: list[str] = []
    all_titles: dict[str, str] = {}
    skip = 0
    take = 20
    total_count = None
    page = 0
    while True:
        data = search(skip, take)
        if total_count is None:
            total_count = data.get("totalCount")
        opps = data.get("opportunities", [])
        page += 1
        print(f"  page {page}: skip={skip} take={take} -> {len(opps)} opportunities")
        if not opps:
            break
        for o in opps:
            all_ids.append(o["Id"])
            all_titles[o["Id"]] = o.get("Title", "")
        skip += take
        if skip >= (total_count or 0):
            break

    print(f"\ntotalCount reported: {total_count}")
    print(f"total opportunities collected: {len(all_ids)}")
    print(f"unique Ids collected: {len(set(all_ids))}")
    dupes = len(all_ids) - len(set(all_ids))
    print(f"duplicate Ids: {dupes}")

    print("\n--- sample of collected titles (first 15) ---")
    for id_ in all_ids[:15]:
        print(f"  {all_titles[id_]!r}")


if __name__ == "__main__":
    main()
