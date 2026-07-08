"""Diagnostic: does appending ANY path (even a wrong guess) to a Workday
tenant differentiate a real tenant from a fake one, the way it did for
Perkins Coie earlier (wd1 was the wrong pod, but /perkinscoieexternal
still returned a 200 XML "Internal Server Error" body -- a real,
non-generic response -- rather than the blank edge-level 406 we now know
bare "/" gives for literally any subdomain, real or fake).

If a wrong-but-plausible site path differs between a known-real tenant
and a known-fake one, that's usable signal even without knowing the
exact site slug. If it doesn't differ, Workday can't be reliably
auto-detected this way at all, and ats_probe.py needs to drop it.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15


def probe(url: str, label: str) -> None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        print(f"  [{label}] {url}")
        print(f"    status={resp.status_code} len={len(resp.text)} content-type={resp.headers.get('content-type')}")
        print(f"    body[:300]: {resp.text[:300]!r}")
    except requests.exceptions.RequestException as exc:
        print(f"  [{label}] {url}\n    EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== Real tenant (dlapiper, wd1 -- correct pod), WRONG site path ===")
    probe("https://dlapiper.wd1.myworkdayjobs.com/nonexistent-site-path-xyz", "real-tenant-wrong-path")

    print("\n=== Real tenant (dlapiper), a couple plausible guesses ===")
    probe("https://dlapiper.wd1.myworkdayjobs.com/dlapiper", "real-tenant-correct-guess")
    probe("https://dlapiper.wd1.myworkdayjobs.com/careers", "real-tenant-generic-guess")

    print("\n=== Known-fake tenant, same wrong site path ===")
    probe("https://thisisnotarealfirmxyz123.wd1.myworkdayjobs.com/nonexistent-site-path-xyz", "fake-tenant-wrong-path")
    probe("https://thisisnotarealfirmxyz123.wd1.myworkdayjobs.com/careers", "fake-tenant-generic-guess")

    print("\n=== Perkins Coie on the WRONG pod (wd1, not wd115), for comparison to what we saw before ===")
    probe("https://perkinscoie.wd1.myworkdayjobs.com/perkinscoieexternal", "real-tenant-wrong-pod-known-path")
    probe("https://perkinscoie.wd1.myworkdayjobs.com/nonexistent-site-path-xyz", "real-tenant-wrong-pod-wrong-path")

    print("\n=== Unknown firms from Wave 1, a couple plausible site-path guesses each ===")
    for tenant in ["kirkland", "lw", "sidley", "cooley"]:
        for guess in [tenant, "careers", f"{tenant}careers", f"{tenant}external"]:
            probe(f"https://{tenant}.wd1.myworkdayjobs.com/{guess}", f"{tenant}/{guess}")


if __name__ == "__main__":
    main()
