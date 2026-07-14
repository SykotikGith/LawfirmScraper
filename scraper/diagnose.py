"""Round 4 (final for this batch) -- 2 remaining leads:

- Ogletree Deakins: careers.ogletree.com/api/jobs works and returns real
  data (round 3), but only 10 jobs came back alongside a "totalCount"
  field whose actual value wasn't printed last round -- this fetches it
  again and prints totalCount plus tries common pagination param names
  (start/num, page, offset) to see which one actually shifts the result
  set.
- Kramer Levin (HSF Kramer): round 3 found the real Phenom REST shape
  (/api/apply/v2/jobs?domain=...) but got "Tenant not identified" for
  domain=careers.hsfkramer.com -- also found phApp.rootDomain in the
  page's embedded config plus a reference to a
  settingsIdentifiersFileUrl on cdn.phenompeople.com, which might reveal
  the real tenant code Phenom expects. This fetches more of that embedded
  phApp.ddo blob and tries a couple of alternate domain param values.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
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


def check_ogletree_deakins() -> None:
    section("Ogletree Deakins -- totalCount value + pagination param probing")
    resp = fetch("https://careers.ogletree.com/api/jobs")
    if resp is None:
        return
    data = resp.json()
    print(f"  totalCount={data.get('totalCount')} count={data.get('count')} jobs_returned={len(data.get('jobs', []))}")
    print(f"  meta_data: {data.get('meta_data')}")

    for params in [
        {"start": 10},
        {"start": 10, "num": 20},
        {"page": 2},
        {"offset": 10},
    ]:
        resp2 = fetch("https://careers.ogletree.com/api/jobs", params=params)
        if resp2 is None:
            continue
        data2 = resp2.json()
        first_title = (data2.get("jobs") or [{}])[0].get("data", {}).get("title")
        print(f"  params={params} -> status={resp2.status_code} jobs={len(data2.get('jobs', []))} first_title={first_title!r}")


def check_kramer_levin() -> None:
    section("Kramer Levin (HSF Kramer) -- hunting for the real Phenom tenant identifier")
    resp = fetch("https://careers.hsfkramer.com/global/en/us/search-results")
    if resp is None:
        return

    ddo_match = re.search(r"phApp\.ddo\s*=\s*(\{.*?\});", resp.text, re.DOTALL)
    if ddo_match:
        try:
            ddo = json.loads(ddo_match.group(1))
            print(f"  phApp.ddo top-level keys: {list(ddo.keys())}")
            site_config = ddo.get("siteConfig", {}).get("data", {})
            print(f"  siteConfig.data keys: {list(site_config.keys())}")
            print(json.dumps(site_config, indent=2)[:1500])
        except json.JSONDecodeError as exc:
            print(f"  phApp.ddo found but failed to parse as JSON: {exc}")
            print(f"  raw[:1000]: {ddo_match.group(1)[:1000]!r}")
    else:
        print("  phApp.ddo assignment not found")

    tenant_hints = re.findall(r'"tenantId"\s*:\s*"([^"]+)"|"tenant"\s*:\s*"([^"]+)"|"orgCode"\s*:\s*"([^"]+)"', resp.text)
    print(f"  tenantId/tenant/orgCode references: {tenant_hints[:10]}")

    for domain_val in ["hsfkramer.com", "hsfkramer", "careers.hsfkramer.com/global/en/us"]:
        url = f"https://careers.hsfkramer.com/api/apply/v2/jobs?domain={domain_val}&start=0&num=10"
        r = fetch(url)
        if r is None:
            continue
        print(f"  domain={domain_val!r} -> status={r.status_code} body[:200]={r.text[:200]!r}")


def main() -> None:
    check_ogletree_deakins()
    check_kramer_levin()


if __name__ == "__main__":
    main()
