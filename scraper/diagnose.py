"""Diagnostic: inspect the actual row/cell structure of O'Melveny's viGlobal
GridView table (id=contentPlaceHolder_gridviewList) to figure out how to
parse it into real postings -- the "Apply" controls are ASP.NET postback
LinkButtons, not real hrefs, so this needs its own adapter rather than the
link-based CustomHTMLAdapter/CircaWorksAdapter pattern.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
URL = "https://ommcareers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx?Tag=84c08942-ea6c-4707-a535-258e400c6b3d"


def main() -> None:
    resp = requests.get(URL, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    soup = BeautifulSoup(resp.text, "lxml")

    table = soup.find("table", id="contentPlaceHolder_gridviewList")
    if table is None:
        print("table not found")
        return

    rows = table.find_all("tr")
    print(f"{len(rows)} <tr> rows total\n")

    for i, row in enumerate(rows[:6]):
        cells = row.find_all(["td", "th"])
        print(f"--- row {i} ({len(cells)} cells) ---")
        for j, cell in enumerate(cells):
            text = cell.get_text(strip=True)
            links = cell.find_all("a")
            link_info = [(a.get("id"), a.get("href"), a.get_text(strip=True)) for a in links]
            print(f"  cell[{j}]: text={text!r} links={link_info}")

    # Check the form action / any hidden fields relevant to postback state,
    # in case we need to POST to page through results or view a detail.
    form = soup.find("form")
    if form is not None:
        print(f"\nform action={form.get('action')!r} method={form.get('method')!r}")
        viewstate = soup.find("input", id="__VIEWSTATE")
        print(f"__VIEWSTATE present: {viewstate is not None}, length: "
              f"{len(viewstate.get('value', '')) if viewstate is not None else 0}")


if __name__ == "__main__":
    main()
