"""AmLaw 100 batch, round 7 (final targeted check before wrapping up):

Sheppard Mullin: __NEXT_DATA__ had no job data directly, but
props.pageProps.componentProps wasn't inspected -- that's where a
component-driven CMS (Sitecore JSS) would reference a job-search widget
and its config/API endpoint, if one exists on this page.

K&L Gates: klgates.recsolu.com/job_boards/1 is JS-rendered (Yello
Enterprise platform) with no visible API path in the initial HTML. Tries
a few common REST API shapes RecSolu/Yello job boards are known to use.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import json
import re

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def fetch(url: str) -> requests.Response | None:
    try:
        return requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as exc:
        print(f"  EXCEPTION fetching {url}: {type(exc).__name__}: {exc}")
        return None


def check_sheppard_component_props() -> None:
    print("=== Sheppard Mullin: componentProps ===")
    resp = fetch("https://www.sheppard.com/careers")
    if resp is None:
        return
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not match:
        print("  no __NEXT_DATA__ block found")
        return
    data = json.loads(match.group(1))
    component_props = data.get("props", {}).get("pageProps", {}).get("componentProps")
    if component_props is None:
        print("  no componentProps key found")
        return
    text = json.dumps(component_props)
    print(f"  componentProps JSON length: {len(text)}")
    print(f"  first 2000 chars: {text[:2000]}")

    job_mentions = re.findall(r'"[^"]{0,40}(?:job|opening|position|search|api)[^"]{0,40}"', text, re.IGNORECASE)
    print(f"\n  keys/values mentioning job/opening/position/search/api: {sorted(set(job_mentions))[:30]}")


def check_klgates_api_guesses() -> None:
    print("\n=== K&L Gates: RecSolu/Yello API endpoint guesses ===")
    board_id_url = "https://klgates.recsolu.com/job_boards/1"
    resp = fetch(board_id_url)
    real_board_id = None
    if resp is not None:
        # the og:url meta tag in round 6's output showed a real opaque board
        # id (o8D4HDBB0N8jcVnRfV263g) different from the "1" in the path
        match = re.search(r'property="og:url"\s+content="[^"]*/job_boards/([\w-]+)"', resp.text)
        if match:
            real_board_id = match.group(1)
            print(f"  real board id found via og:url: {real_board_id}")

    candidates = [
        "https://klgates.recsolu.com/api/v1/job_boards/1/jobs",
        "https://klgates.recsolu.com/api/job_boards/1/jobs",
        "https://klgates.recsolu.com/job_boards/1.json",
        "https://klgates.recsolu.com/job_boards/1/jobs.json",
    ]
    if real_board_id:
        candidates += [
            f"https://klgates.recsolu.com/api/v1/job_boards/{real_board_id}/jobs",
            f"https://klgates.recsolu.com/job_boards/{real_board_id}.json",
        ]

    for url in candidates:
        headers = dict(DEFAULT_HEADERS)
        headers["Accept"] = "application/json"
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.RequestException as exc:
            print(f"  {url}: EXCEPTION {type(exc).__name__}")
            continue
        print(f"  {url}: status={r.status_code} content-type={r.headers.get('Content-Type')} len={len(r.text)}")
        if r.status_code == 200 and "json" in (r.headers.get("Content-Type") or ""):
            print(f"    first 500 chars: {r.text[:500]}")


def main() -> None:
    check_sheppard_component_props()
    check_klgates_api_guesses()


if __name__ == "__main__":
    main()
