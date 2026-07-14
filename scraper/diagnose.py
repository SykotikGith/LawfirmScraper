"""Round 4 (final) -- just Dechert left. Round 3 found the real embedded
config: {"careerSearchPath": "/bin/careersSearch", "type": "getCareers",
"locationsEndpoint": ".careerlocations.json?123", "positionsOpt": [...
"Business Professional" among the real filter values]}. This is an AEM
(Adobe Experience Manager) Sling servlet -- careerSearchPath is rooted at
the domain, not the page's own JCR path. Trying a GET and POST against it
with a few parameter shape guesses based on the embedded config's own key
names.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

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


def main() -> None:
    section("Dechert -- probing /bin/careersSearch directly")
    base = "https://www.dechert.com/bin/careersSearch"

    candidates = [
        ("GET, type only", "GET", {"type": "getCareers"}, None),
        ("GET, type + position", "GET", {"type": "getCareers", "position": "Business Professional"}, None),
        ("GET, type + positionType", "GET", {"type": "getCareers", "positionType": "Business Professional"}, None),
        ("POST JSON, type only", "POST", None, {"type": "getCareers"}),
        (
            "POST JSON, type + position",
            "POST",
            None,
            {"type": "getCareers", "position": "Business Professional"},
        ),
    ]

    for label, method, params, json_body in candidates:
        kwargs = {}
        if params:
            kwargs["params"] = params
        if json_body:
            kwargs["json"] = json_body
        resp = fetch(base, method=method, **kwargs)
        if resp is None:
            print(f"  [{label}] -> EXCEPTION (see above)")
            continue
        print(f"  [{label}] -> status={resp.status_code} len={len(resp.text)}")
        if resp.status_code == 200:
            print(f"    body[:500]: {resp.text[:500]!r}")

    section("Dechert -- also checking the locations endpoint for shape clues")
    loc_resp = fetch("https://www.dechert.com/content/dechert/en/careers.careerlocations.json")
    if loc_resp:
        print(f"  status={loc_resp.status_code} len={len(loc_resp.text)}")
        if loc_resp.status_code == 200:
            print(f"  body[:500]: {loc_resp.text[:500]!r}")


if __name__ == "__main__":
    main()
