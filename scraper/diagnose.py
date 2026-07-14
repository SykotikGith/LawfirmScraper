"""Round 2: WorkdayAdapter's naive tenant-from-URL-path guess failed with an
SSL hostname mismatch on vhr_wachtelllipton.wd1.myworkdayjobs.com --
underscores aren't valid in real hostnames and wildcard certs won't cover
one, so that's almost certainly not the real CXS API subdomain. The
myworkdaysite.com front-end path segment doesn't always equal the
underlying tenant slug 1:1 (it did for White & Case/Norton Rose Fulbright,
but evidently not here).

This fetches the real recruiting page directly and searches it for any
embedded reference to the actual old-style {tenant}.{pod}.myworkdayjobs.com
API (both raw domain mentions and any inline JSON config), and also tries
a couple of direct-request fallbacks: hitting the CXS path straight off
the wd1.myworkdaysite.com domain itself, and trying "wachtelllipton"
(the vhr_ prefix stripped) as the tenant.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20
RECRUITING_URL = "https://wd1.myworkdaysite.com/recruiting/vhr_wachtelllipton/wlrk"


def fetch(url: str, method: str = "GET", **kwargs) -> requests.Response | None:
    try:
        if method == "GET":
            return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
        return requests.post(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return None


def inspect_recruiting_page() -> None:
    print(f"=== fetching {RECRUITING_URL} ===")
    resp = fetch(RECRUITING_URL)
    if resp is None:
        return
    print(f"  status={resp.status_code}  final_url={resp.url}  len={len(resp.text)}")
    text = resp.text

    myworkdayjobs_mentions = re.findall(r"[\w.-]*\.myworkdayjobs\.com[^\s\"'\\]*", text)
    print(f"  myworkdayjobs.com mentions ({len(myworkdayjobs_mentions)}): {sorted(set(myworkdayjobs_mentions))[:10]}")

    cxs_mentions = re.findall(r"/wday/cxs/[\w./-]*", text)
    print(f"  /wday/cxs/ path mentions ({len(cxs_mentions)}): {sorted(set(cxs_mentions))[:10]}")

    tenant_hints = re.findall(r'"tenant"\s*:\s*"([^"]+)"', text)
    print(f"  inline \"tenant\": ... references: {sorted(set(tenant_hints))}")


def try_cxs_variants() -> None:
    print("\n=== trying CXS API request variants ===")
    body = {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": ""}

    candidates = [
        ("direct off myworkdaysite.com domain", "https://wd1.myworkdaysite.com/wday/cxs/vhr_wachtelllipton/wlrk/jobs"),
        ("vhr_ prefix stripped, old-style", "https://wachtelllipton.wd1.myworkdayjobs.com/wday/cxs/wachtelllipton/wlrk/jobs"),
        ("site as tenant, old-style", "https://wlrk.wd1.myworkdayjobs.com/wday/cxs/wlrk/wlrk/jobs"),
    ]
    for label, url in candidates:
        resp = fetch(url, method="POST", json=body)
        if resp is None:
            print(f"  {label}: {url} -> EXCEPTION (see above)")
            continue
        print(f"  {label}: {url}\n    status={resp.status_code}  len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:300]: {resp.text[:300]!r}")


def main() -> None:
    inspect_recruiting_page()
    try_cxs_variants()


if __name__ == "__main__":
    main()
