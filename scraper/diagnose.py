"""Round 3 for the last 2 leads.

- Dechert: round 2 found a "Business Professional" filter-option value
  embedded in the page's JS config (part of a larger filter dropdown
  blob including "Judicial Clerk" etc.) -- confirms a real filterable
  job board exists, but not yet the actual listing data or API. This
  pulls a much wider context window around that snippet to find the
  surrounding JSON structure, and searches for any adjacent API/endpoint
  reference.
- Akin Gump: round 2's app.jobsearch/app.joblist fuseaction guesses (the
  trick that worked for WilmerHale) all came back with zero jobid= links
  despite real 200 responses -- this dumps the actual search FORM's
  hidden input fields (SilkRoad forms often require specific hidden
  tokens/params to return real results) and tries submitting it with
  those defaults via POST.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

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


def check_dechert() -> None:
    section("Dechert -- wide context around the 'Business Professional' filter blob")
    resp = fetch("https://www.dechert.com/careers.html")
    if resp is None:
        return
    idx = resp.text.find("Business Professional")
    if idx == -1:
        print("  'Business Professional' not found this time (unexpected)")
        return
    start = max(0, idx - 2000)
    end = min(len(resp.text), idx + 2000)
    print(f"  context[{start}:{end}]:\n{resp.text[start:end]}")

    endpoint_hints = re.findall(r'"(https?://[^"]*(?:search|jobs|careers|api)[^"]*)"', resp.text, re.I)
    print(f"\n  search/jobs/careers/api-looking absolute URLs anywhere on page: {sorted(set(endpoint_hints))[:15]}")


def check_akin_gump() -> None:
    section("Akin Gump -- dumping search form hidden fields, trying a submission")
    resp = fetch("https://jobs.silkroad.com/AkinGump/AkinGump")
    if resp is None:
        return
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    forms = soup.find_all("form")
    print(f"  forms found: {len(forms)}")
    for form in forms:
        action = form.get("action")
        method = form.get("method")
        hidden_inputs = {
            inp.get("name"): inp.get("value", "")
            for inp in form.find_all("input", type="hidden")
            if inp.get("name")
        }
        print(f"  --- form action={action!r} method={method!r}")
        print(f"      hidden inputs: {hidden_inputs}")

        if action and method and method.lower() == "post":
            full_action = action if action.startswith("http") else f"https://jobs.silkroad.com{action}"
            submit_resp = fetch(full_action, method="POST", data=hidden_inputs)
            if submit_resp is None:
                continue
            print(f"      POST to {full_action} -> status={submit_resp.status_code} len={len(submit_resp.text)}")
            job_links = re.findall(r'<a[^>]+href="([^"]*jobid=\d+[^"]*)"[^>]*>([^<]+)</a>', submit_resp.text, re.I)
            print(f"      jobid= links found: {len(job_links)}")
            for href, text in job_links[:10]:
                print(f"        {text.strip()!r} -> {href}")


def main() -> None:
    check_dechert()
    check_akin_gump()


if __name__ == "__main__":
    main()
