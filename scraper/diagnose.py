"""Diagnostic: why did ats_probe.py's Workday check return 406 for all 69
firms uniformly? That's not believable as real per-tenant signal -- test
known-good Workday tenants (dlapiper=wd1, clydeco=wd103,
perkinscoie=wd115, all confirmed real elsewhere in this project) against
a definitely-fake tenant name, with full headers/body, to find whatever
actually differentiates a real tenant from a nonexistent one despite the
shared 406 status.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15

CONTROLS = [
    ("dlapiper", "wd1", "known-good"),
    ("clydeco", "wd103", "known-good"),
    ("perkinscoie", "wd115", "known-good"),
    ("thisisnotarealfirmxyz123", "wd1", "known-fake"),
    ("kirkland", "wd1", "unknown (Wave 1 result)"),
]


def probe(host: str, headers: dict, label: str) -> None:
    try:
        resp = requests.get(f"https://{host}/", headers=headers, timeout=TIMEOUT, allow_redirects=True)
        print(f"  [{label}] status={resp.status_code} len={len(resp.text)} "
              f"content-type={resp.headers.get('content-type')}")
        print(f"    headers: {dict(resp.headers)}")
        print(f"    body[:300]: {resp.text[:300]!r}")
    except requests.exceptions.RequestException as exc:
        print(f"  [{label}] EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== Round A: default probe headers (same as ats_probe.py) ===")
    for tenant, wd, kind in CONTROLS:
        host = f"{tenant}.{wd}.myworkdayjobs.com"
        print(f"\n{host} ({kind})")
        probe(host, DEFAULT_HEADERS, "default-headers")

    print("\n\n=== Round B: browser-like Accept header ===")
    browser_headers = {
        **DEFAULT_HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    for tenant, wd, kind in CONTROLS:
        host = f"{tenant}.{wd}.myworkdayjobs.com"
        print(f"\n{host} ({kind})")
        probe(host, browser_headers, "browser-headers")

    print("\n\n=== Round C: DNS resolution only (no HTTP) ===")
    import socket
    for tenant, wd, kind in CONTROLS:
        host = f"{tenant}.{wd}.myworkdayjobs.com"
        try:
            ip = socket.gethostbyname(host)
            print(f"  {host} ({kind}): resolves to {ip}")
        except socket.gaierror as exc:
            print(f"  {host} ({kind}): DNS FAILURE {exc}")


if __name__ == "__main__":
    main()
