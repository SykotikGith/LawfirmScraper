"""Round 6 diagnostic: Fisher Phillips only.

job-openings.php is a *search form* -- it shows "Select options from the
menus above and click Search" until submitted. Parse the form and submit
it with empty/default values to get the full results list, then inspect
what comes back. (Round 5's attempt at this crashed on a urljoin bug --
fixed here.)

Marshall Dennehey and Reed Smith are dropped from this round:
Marshall Dennehey's /careers/administrative-professionals turned out to be
another marketing page with no listings ("submit your resume" model, not
a job board) -- treat it as needing a periodic manual check rather than a
scraper. Reed Smith needs an actual browser DevTools Network tab to find
its real data call; static URL guessing hit a dead end.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


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

    submit_url = urljoin(url, action)
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
    fisher_phillips()


if __name__ == "__main__":
    main()
