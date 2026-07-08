"""Diagnostic: is careers-{slug}.icims.com wildcard/shared-edge like
myworkdayjobs.com was, or does it genuinely differentiate real tenants
from made-up ones?

ats_probe.py's latest run got an identical 405 for 51 of 69 firms on the
iCIMS pattern -- the same status code our 3 CONFIRMED real iCIMS tenants
(grsm, lewisbrisbois, orrick, already in config.py) return when blocked
by their AWS WAF "Human Verification" challenge. A uniform result across
51 unrelated subdomains is exactly the shape of the false signal we just
found and fixed for Workday, so don't trust it without checking.

Tests: DNS resolution (unlike Workday, iCIMS subdomains should be
individually provisioned per customer, not wildcarded -- if that's true,
a fake slug should fail DNS resolution entirely rather than returning a
same-looking 405) and response body comparison between known-real and
known-fake tenants.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import socket

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15

KNOWN_REAL = ["grsm", "lewisbrisbois", "orrick"]
KNOWN_FAKE = ["thisisnotarealfirmxyz123", "totallymadeupslugabc999"]
UNKNOWN_FROM_WAVE = ["kirkland", "sidley", "quinnemanuel"]


def check_dns(slug: str, kind: str) -> None:
    host = f"careers-{slug}.icims.com"
    try:
        ip = socket.gethostbyname(host)
        print(f"  {host} ({kind}): resolves to {ip}")
    except socket.gaierror as exc:
        print(f"  {host} ({kind}): DNS FAILURE {exc}")


def check_http(slug: str, kind: str) -> None:
    host = f"careers-{slug}.icims.com"
    url = f"https://{host}/"
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
        print(f"  {host} ({kind}): status={resp.status_code} len={len(resp.text)}")
        print(f"    body[:200]: {resp.text[:200]!r}")
    except requests.exceptions.RequestException as exc:
        print(f"  {host} ({kind}): EXCEPTION {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== DNS resolution ===")
    for slug in KNOWN_REAL:
        check_dns(slug, "known-real")
    for slug in KNOWN_FAKE:
        check_dns(slug, "known-fake")
    for slug in UNKNOWN_FROM_WAVE:
        check_dns(slug, "unknown-from-probe")

    print("\n=== HTTP response ===")
    for slug in KNOWN_REAL:
        check_http(slug, "known-real")
    for slug in KNOWN_FAKE:
        check_http(slug, "known-fake")
    for slug in UNKNOWN_FROM_WAVE:
        check_http(slug, "unknown-from-probe")


if __name__ == "__main__":
    main()
