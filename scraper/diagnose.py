"""Verify Wachtell Lipton's real Workday tenant, given directly by the user:
https://wd1.myworkdaysite.com/recruiting/vhr_wachtelllipton/wlrk

Parses as tenant=vhr_wachtelllipton, pod=wd1, site=wlrk (the newer
myworkdaysite.com front-end shape, same pattern as White & Case and
Norton Rose Fulbright -- still routes to the standard old-style CXS API,
WorkdayAdapter needs no changes). Site slug is already known here, so no
need to guess it the way verify_batch.py does for other Workday hits --
just fetch directly and check for real postings.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

from .adapters.workday import WorkdayAdapter


def main() -> None:
    adapter = WorkdayAdapter(
        "Wachtell Lipton",
        {"tenant": "vhr_wachtelllipton", "wd": "wd1", "site": "wlrk"},
    )
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH FAILED: {type(exc).__name__}: {exc}")
        return

    print(f"{len(postings)} postings")
    for p in postings[:15]:
        print(f"  - {p.title} — {p.location}")


if __name__ == "__main__":
    main()
