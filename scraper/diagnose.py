"""Diagnostic round 4 for Reed Smith: the AJAX grid endpoint returns real
HTML with "Page 1 of 5" and pagination links shaped like
?movejump=1&movejump_page=N&pagestamp=<token>. Round 3's printout cut off
right where the actual job rows start. This parses the grid HTML with
BeautifulSoup to find the real per-job link markup, and sweeps all 5 pages
using the same session/pagestamp to see the full job list before writing
the real adapter.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 30
LIST_URL = "https://careers.reedsmith.com/jobs/vacancy/find/results"
PAGESTAMP_RE = re.compile(r"ajaxaction/posbrowser_gridhandler/\?pagestamp=([\w-]+)")


def fetch_grid(session: requests.Session, pagestamp: str, page: int) -> str:
    if page == 1:
        url = f"{LIST_URL}/ajaxaction/posbrowser_gridhandler/?pagestamp={pagestamp}"
    else:
        url = f"{LIST_URL}/ajaxaction/posbrowser_gridhandler/?movejump=1&movejump_page={page}&pagestamp={pagestamp}"
    headers = dict(DEFAULT_HEADERS)
    headers["X-Requested-With"] = "XMLHttpRequest"
    headers["Referer"] = LIST_URL
    resp = session.get(url, headers=headers, timeout=TIMEOUT)
    return resp.text


def main() -> None:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    list_resp = session.get(LIST_URL, timeout=TIMEOUT)
    match = PAGESTAMP_RE.search(list_resp.text)
    if not match:
        print("no pagestamp found")
        return
    pagestamp = match.group(1)
    print(f"pagestamp: {pagestamp}\n")

    page1_html = fetch_grid(session, pagestamp, 1)
    soup = BeautifulSoup(page1_html, "lxml")

    print("=== all <a> tags inside ListGridContainer/rowContainerHolder-ish areas ===")
    grid_container = soup.select_one(".ListGridContainer") or soup
    links = grid_container.find_all("a")
    print(f"total <a> tags found in grid area: {len(links)}")
    for link in links[:30]:
        href = link.get("href", "")
        text = link.get_text(strip=True)
        cls = link.get("class")
        print(f"  href={href!r}  class={cls}  text={text!r}")

    print("\n=== elements with class containing 'row' (likely one per job) ===")
    row_els = soup.select("[class*=row]")
    print(f"count: {len(row_els)}")
    for el in row_els[:5]:
        print(f"\n--- row element (tag={el.name}, class={el.get('class')}) ---")
        print(str(el)[:1500])

    print("\n\n=== sweeping all 5 pages, counting distinct job links ===")
    all_hrefs: set[str] = set()
    for page in range(1, 6):
        html = fetch_grid(session, pagestamp, page)
        page_soup = BeautifulSoup(html, "lxml")
        page_links = [a.get("href", "") for a in page_soup.select(".ListGridContainer a, .rowContainerHolder a")]
        job_like = [h for h in page_links if h and "ajaxaction" not in h and "/map/" not in h]
        print(f"  page {page}: {len(job_like)} candidate job links (of {len(page_links)} total <a> in grid)")
        all_hrefs.update(job_like)

    print(f"\ntotal distinct candidate job links across all pages: {len(all_hrefs)}")
    for h in sorted(all_hrefs)[:15]:
        print(f"  {h}")


if __name__ == "__main__":
    main()
