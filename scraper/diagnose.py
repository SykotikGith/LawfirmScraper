"""Round 5 diagnostic.

- Marshall Dennehey: the sitemap only has marketing landing pages, but
  /careers/administrative-professionals (the business-professional track,
  found via sitemap) hasn't been inspected yet -- check whether it lists
  real openings or embeds a widget.
- Fisher Phillips: job-openings.php is a *search form* -- it shows
  "Select options from the menus above and click Search" until submitted.
  Parse the form and submit it with empty/default values to get the full
  results list, then inspect what comes back.

Reed Smith is intentionally left out of this round -- every URL guess so
far returns the same ~141KB SPA shell regardless of path, meaning the
real data call isn't discoverable by guessing. That one needs an actual
browser DevTools Network tab to find the XHR/fetch call.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def marshall_dennehey() -> None:
    print("\n=== Marshall Dennehey: /careers/administrative-professionals ===")
    url = "https://www.marshalldennehey.com/careers/administrative-professionals"
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    print(f"status={resp.status_code} len={len(resp.text)}")
    text = resp.text
    iframes = re.findall(r'<iframe[^>]+src="([^"]+)"', text)
    print(f"iframes: {iframes}")
    for hint in ["icims", "workday", "greenhouse", "lever.co", "smartrecruiters",
                 "clearcompany", "hrmdirect", "applicantstack", "paylocity",
                 "oraclecloud", "avature", "phenompeople", "adp.com"]:
        if hint in text.lower():
            idx = text.lower().find(hint)
            print(f"  found ATS hint '{hint}':", text[max(0, idx - 100):idx + 150].replace("\n", " "))
    soup = BeautifulSoup(text, "lxml")
    links = [a.get("href", "") for a in soup.select("a[href]")]
    job_like = [h for h in links if any(k in h.lower() for k in ["job", "opening", "position", "career"])]
    print(f"job-like links found (first 15 of {len(job_like)}):")
    for h in job_like[:15]:
        print(" ", h)


def fisher_phillips() -> None:
    print("\n=== Fisher Phillips: submitting the search form ===")
    url = "https://fisherphillips.hrmdirect.com/employment/job-openings.php"
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    resp = session.get(url, timeout=TIMEOUT)
    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form")
    if form is None:
        print("no <form> found on the page")
        return
    action = form.get("action") or url
    method = (form.get("method") or "GET").upper()
    print(f"form action={action!r} method={method}")

    fields = {}
    for inp in form.find_all(["input", "select"]):
        name = inp.get("name")
        if not name:
            continue
        if inp.name == "select":
            selected = inp.find("option", selected=True) or inp.find("option")
            fields[name] = selected.get("value", "") if selected else ""
        else:
            fields[name] = inp.get("value", "")
    print(f"form fields: {fields}")

    submit_url = action if action.startswith("http") else f"https://fisherphillips.hrmdirect.com{action}"
    if method == "POST":
        result = session.post(submit_url, data=fields, timeout=TIMEOUT)
    else:
        result = session.get(submit_url, params=fields, timeout=TIMEOUT)
    print(f"submitted search -> status={result.status_code} url={result.url} len={len(result.text)}")
    print(f"'reqResult' occurrences in response: {result.text.count('reqResult')}")
    print(f"'noResultsMsg' occurrences: {result.text.count('noResultsMsg')}")
    hrefs = re.findall(r'href="([^"]*(?:job-opening|view\.php\?req)[^"]*)"', result.text)
    print(f"job hrefs found (first 10 of {len(hrefs)}):")
    for h in hrefs[:10]:
        print(" ", h)


def main() -> None:
    marshall_dennehey()
    fisher_phillips()


if __name__ == "__main__":
    main()
