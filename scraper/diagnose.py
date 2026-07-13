"""AmLaw 100 batch, round 6: chase the 2 genuine finds from round 5.

K&L Gates: found a link to https://klgates.recsolu.com/job_boards/1 --
RecSolu, a platform not in this project's known-ATS pattern list at all
(that's why the broad sniff missed it despite the link being right
there). Fetches it directly to see the structure -- HTML table, JSON API,
or JS app -- before deciding whether it's worth a new adapter.

Sheppard Mullin: the /careers page's __NEXT_DATA__ blob (Sitecore + Next.js
JSS) is 80KB but round 5 only printed the first 1500 chars, which was
just page metadata/badges, not job data. Searches the full JSON for
job/opening/position/requisition-shaped keys to find where the real
listing data lives.

Crowell & Moring: the careers landing page was an unusual 4MB -- quick
check for an embedded JSON state blob (same shape as Sheppard Mullin's
Next.js pattern) before writing this off entirely.

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


def check_klgates_recsolu() -> None:
    print("=== K&L Gates: klgates.recsolu.com/job_boards/1 ===")
    resp = fetch("https://klgates.recsolu.com/job_boards/1")
    if resp is None:
        return
    print(f"  status={resp.status_code}  final_url={resp.url}  len={len(resp.text)}")
    text = resp.text
    print(f"  'application/json' content-type: {resp.headers.get('Content-Type')}")

    script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
    print(f"  <script src> tags ({len(script_srcs)}): {script_srcs[:10]}")

    api_hints = re.findall(r'["\'](/[\w./-]*(?:api|job|posting|search)[\w./-]*)["\']', text, re.IGNORECASE)
    print(f"  possible API path fragments: {sorted(set(api_hints))[:20]}")

    job_link_count = len(re.findall(r'/jobs?/', text, re.IGNORECASE))
    print(f"  '/job(s)/' occurrences in raw HTML: {job_link_count}")
    print(f"  first 1200 chars:\n  {text[:1200]!r}")


def check_sheppard_mullin_next_data() -> None:
    print("\n=== Sheppard Mullin: searching __NEXT_DATA__ for job data ===")
    resp = fetch("https://www.sheppard.com/careers")
    if resp is None:
        return
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not match:
        print("  no __NEXT_DATA__ block found this time")
        return
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        print(f"  JSON PARSE FAILED: {exc}")
        return

    def find_job_keys(obj, path="root", depth=0, results=None):
        if results is None:
            results = []
        if depth > 12:
            return results
        if isinstance(obj, dict):
            for k, v in obj.items():
                if re.search(r"job|opening|position|requisition|vacan", k, re.IGNORECASE):
                    results.append((f"{path}.{k}", type(v).__name__, str(v)[:200]))
                find_job_keys(v, f"{path}.{k}", depth + 1, results)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:5]):
                find_job_keys(item, f"{path}[{i}]", depth + 1, results)
        return results

    hits = find_job_keys(data)
    print(f"  job-related keys found in __NEXT_DATA__: {len(hits)}")
    for path, typ, preview in hits[:20]:
        print(f"    {path} ({typ}): {preview}")

    # also print the overall top-level shape for orientation
    print(f"\n  top-level keys: {list(data.keys())}")
    if "props" in data and "pageProps" in data.get("props", {}):
        print(f"  props.pageProps keys: {list(data['props']['pageProps'].keys())}")


def check_crowell_json() -> None:
    print("\n=== Crowell & Moring: checking for embedded JSON state ===")
    resp = fetch("https://www.crowell.com/en/careers")
    if resp is None:
        return
    text = resp.text
    print(f"  len={len(text)}")
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.DOTALL)
    print(f"  __NEXT_DATA__ present: {bool(next_data)}")
    large_script_blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.{5000,})?</script>", text, re.DOTALL)
    print(f"  inline <script> blocks over 5000 chars: {len(large_script_blocks)}")
    if large_script_blocks:
        print(f"  first 500 chars of largest: {large_script_blocks[0][:500]!r}")


def main() -> None:
    check_klgates_recsolu()
    check_sheppard_mullin_next_data()
    check_crowell_json()


if __name__ == "__main__":
    main()
