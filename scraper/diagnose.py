"""Round 2 for the last 2 unresolved hits: Bryan Cave Leighton Paisner
(viGlobal, different template than O'Melveny's) and Davis Wright Tremaine
(Jobvite JS shell, but job links present somewhere in a small 17KB page).

BCLP: neither URL tried last round was the real "all current postings"
listing -- one showed a generic placeholder, one showed a single filtered
job. This re-fetches the careers page looking for EVERY viglobalcloud.com
link (not just the first), to find a general/unfiltered listing link
distinct from the specific-job one already found. Also parses the bare
RecDefault.aspx response with BeautifulSoup to count real <tr> rows in
the gridview table and print each one's raw text, since the row markup
here (h4/h5 tags) is structured differently than O'Melveny's
concatenated-text-blob rows -- ViGlobalAdapter's regex won't parse this
tenant's HTML shape without changes.

DWT: searches for embedded JSON (JSON-LD script blocks, inline `jobs =`
assignments) that might carry full job data server-side for SEO, even
though the visible page is a Jobvite JS app.

Usage: python -m scraper.diagnose
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 20


def check_bclp() -> None:
    print("=== Bryan Cave Leighton Paisner: finding the real listing URL ===")
    careers_url = "https://www.bclplaw.com/en-US/careers.html"
    resp = requests.get(careers_url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    links = sorted(set(re.findall(r'href="(https://bclplaw-careers\.viglobalcloud\.com[^"]*)"', resp.text)))
    print(f"  all viglobalcloud.com links found on {careers_url} ({len(links)}):")
    for link in links:
        print(f"    {link}")

    print("\n  parsing bare RecDefault.aspx gridview table with BeautifulSoup:")
    bare_url = "https://bclplaw-careers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx"
    resp2 = requests.get(bare_url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    soup = BeautifulSoup(resp2.text, "lxml")
    table = soup.find("table", id="contentPlaceHolder_gridviewList")
    if table is None:
        print("    no table with that id found")
        return
    rows = table.find_all("tr")
    print(f"    {len(rows)} <tr> rows found")
    for row in rows[:6]:
        h4 = row.find("h4")
        h5s = row.find_all("h5")
        title = h4.get_text(strip=True) if h4 else None
        fields = {h5.get_text(strip=True).split(" ")[0]: h5.get_text(strip=True) for h5 in h5s}
        print(f"    title={title!r}  fields={fields}")


def check_dwt() -> None:
    print("\n=== Davis Wright Tremaine: looking for embedded job JSON ===")
    resp = requests.get("https://jobs.jobvite.com/dwt/", headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    text = resp.text

    ld_json_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.DOTALL)
    print(f"  JSON-LD script blocks found: {len(ld_json_blocks)}")
    for block in ld_json_blocks[:3]:
        print(f"    {block[:500]}")

    inline_assigns = re.findall(r'(var|window\.)\s*(\w*[jJ]obs?\w*)\s*=\s*(\[.{0,300})', text)
    print(f"  inline job-like variable assignments found: {len(inline_assigns)}")
    for prefix, name, snippet in inline_assigns[:5]:
        print(f"    {prefix}{name} = {snippet}...")

    soup = BeautifulSoup(text, "lxml")
    job_links = soup.select("a[href*='/dwt/job/']")
    print(f"  <a href*='/dwt/job/'> anchor tags found: {len(job_links)}")
    for a in job_links[:10]:
        print(f"    href={a.get('href')!r}  text={a.get_text(strip=True)!r}")

    # look at raw context around one job id from the earlier run, in case
    # it's inside a data-* attribute or JSON string rather than a plain <a>
    idx = text.find("/dwt/job/")
    if idx != -1:
        print(f"\n  raw context around first '/dwt/job/' occurrence:\n  ...{text[max(0,idx-300):idx+300]}...")


def main() -> None:
    check_bclp()
    check_dwt()


if __name__ == "__main__":
    main()
