"""Find the real Workday tenant/pod/site for firms already confirmed to be
on Workday (via ats_probe.py's path-specific-error signal) but whose site
slug couldn't be guessed by verify_batch.py's brute-force template list.

Same technique that found Goodwin Procter's real endpoint
(goodwinprocter.wd5.myworkdayjobs.com/External_Careers, embedded directly
in goodwinlaw.com/en/careers) and Wilson Elser's real Greenhouse token:
check the firm's own marketing careers page for an embedded ATS link,
rather than keep guessing site-slug suffixes blind.

Usage: python -m scraper.find_workday_sites
Writes find_workday_sites_results.md alongside printing to stdout.
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS
from .adapters.workday import WorkdayAdapter

TIMEOUT = 20

WORKDAY_URL_RE = re.compile(
    r"https?://([a-zA-Z0-9\-]+)\.(wd\d+)\.myworkdayjobs\.com/([a-zA-Z0-9_\-]+)"
)

# (firm, domain, [candidate paths])
# Current batch: the 7 confirmed-Workday-tenant firms from the AmLaw 100
# expansion round whose site slug verify_batch.py's brute-force template
# guesses didn't find (July 2026).
FIRMS: list[tuple[str, str, list[str]]] = [
    ("McDermott Will & Emery", "www.mwe.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Morrison & Foerster", "www.mofo.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Skadden Arps", "www.skadden.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Davis Polk", "www.davispolk.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Hogan Lovells", "www.hoganlovells.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Cleary Gottlieb", "www.clearygottlieb.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
    ("Norton Rose Fulbright", "www.nortonrosefulbright.com", ["/careers", "/en/careers", "/en-us/careers", ""]),
]


def find_link(firm: str, domain: str, paths: list[str]) -> tuple[str, str, str] | None:
    for path in paths:
        url = f"https://{domain}{path}"
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        except requests.exceptions.RequestException as exc:
            print(f"  {url}: EXCEPTION {type(exc).__name__}: {exc}")
            continue
        print(f"  {url}: status={resp.status_code} len={len(resp.text)}")
        match = WORKDAY_URL_RE.search(resp.text)
        if match:
            tenant, pod, site = match.groups()
            print(f"    found Workday link: tenant={tenant} pod={pod} site={site}")
            return tenant, pod, site
    return None


def main() -> None:
    results = []
    for firm, domain, paths in FIRMS:
        print(f"\n=== {firm} ===")
        found = find_link(firm, domain, paths)
        if found is None:
            results.append({"firm": firm, "status": "NOT FOUND", "sample_titles": [], "config_snippet": None})
            continue

        tenant, pod, site = found
        adapter = WorkdayAdapter(firm, {"tenant": tenant, "wd": pod, "site": site})
        try:
            postings = adapter.fetch()
        except Exception as exc:  # noqa: BLE001
            results.append({"firm": firm, "status": f"LINK FOUND BUT FETCH FAILED: {exc}",
                             "sample_titles": [], "config_snippet": None})
            continue

        sample = [p.title for p in postings[:5]]
        snippet = (
            f'"{firm}": {{\n'
            f'    "adapter": WorkdayAdapter,\n'
            f'    "tenant": "{tenant}",\n'
            f'    "wd": "{pod}",\n'
            f'    "site": "{site}",\n'
            f'}},'
        )
        results.append({
            "firm": firm,
            "status": f"OK -- {len(postings)} postings (tenant={tenant}, pod={pod}, site={site})",
            "sample_titles": sample,
            "config_snippet": snippet,
        })
        print(f"  {len(postings)} postings fetched")
        for t in sample:
            print(f"    - {t}")

    with open("find_workday_sites_results.md", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"## {r['firm']}\n")
            f.write(f"Status: {r['status']}\n\n")
            if r["sample_titles"]:
                f.write("Sample titles:\n")
                for t in r["sample_titles"]:
                    f.write(f"- {t}\n")
            if r["config_snippet"]:
                f.write("\nConfig snippet:\n```python\n")
                f.write(r["config_snippet"])
                f.write("\n```\n")
            f.write("\n")

    print("\nWritten to find_workday_sites_results.md")


if __name__ == "__main__":
    main()
