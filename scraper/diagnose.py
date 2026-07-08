"""Diagnostic: verify Goodwin Procter's real Workday endpoint, found
embedded in goodwinlaw.com/en/careers
(https://goodwinprocter.wd5.myworkdayjobs.com/External_Careers) -- a
completely different tenant/pod/site than the Greenhouse "goodwin" guess
that returned only 1 thin, non-obviously-legal posting earlier. That
Greenhouse hit was very likely also a false collision, the same way the
Winston & Strawn/HRMdirect "winston" guess turned out to belong to an
unrelated company.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

from .adapters.workday import WorkdayAdapter


def main() -> None:
    adapter = WorkdayAdapter(
        "Goodwin Procter",
        {"tenant": "goodwinprocter", "wd": "wd5", "site": "External_Careers"},
    )
    postings = adapter.fetch()
    print(f"Goodwin Procter (Workday, goodwinprocter.wd5, site=External_Careers): "
          f"{len(postings)} postings")
    for p in postings[:10]:
        print(f"  - {p.title} — {p.location}")


if __name__ == "__main__":
    main()
