"""PageUp/eArcu adapter.

eArcu (PageUp Europe) career sites render the initial list page as a shell
with no job data in static HTML -- the actual results grid loads via an
AJAX call after page load:
  <list_url>/ajaxaction/posbrowser_gridhandler/?pagestamp=<token>[&movejump=1&movejump_page=N]
The pagestamp token is generated per page load and extracted from an
inline <script> on the list page; it's tied to session cookies
(earcusessionid/earcusession) set by that same request, so the AJAX calls
must reuse the same session that fetched the list page.

CONFIRMED via live probing (Reed Smith, July 2026): each grid page returns
up to 12 job rows as an HTML fragment (not JSON). Sweeping movejump_page
from 1 upward until a page returns 0 rows retrieves every posting exactly
once (verified end-to-end: 54/54 unique postings across 5 pages). Each row
(.rowContainerHolder) has a title link (.rowLabel a, href ending in
/<numeric-id>/description/) and a location span
(.codelist5value_vacancyColumn) -- both extracted directly from the
already-fetched grid HTML, no per-job request needed.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

PAGESTAMP_RE = re.compile(r"ajaxaction/posbrowser_gridhandler/\?pagestamp=([\w-]+)")
ID_RE = re.compile(r"/(\d+)/description/?$")
MAX_PAGES_SAFETY_CAP = 100


class EArcuAdapter(Adapter):
    ats_name = "eArcu"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"].rstrip("/")

        list_resp = self.session.get(list_url, timeout=30)
        list_resp.raise_for_status()
        match = PAGESTAMP_RE.search(list_resp.text)
        if not match:
            return []
        pagestamp = match.group(1)

        ajax_headers = {"X-Requested-With": "XMLHttpRequest", "Referer": list_url}

        postings: list[Posting] = []
        seen_ids: set[str] = set()
        page = 1
        while page <= MAX_PAGES_SAFETY_CAP:
            if page == 1:
                url = f"{list_url}/ajaxaction/posbrowser_gridhandler/?pagestamp={pagestamp}"
            else:
                url = (
                    f"{list_url}/ajaxaction/posbrowser_gridhandler/"
                    f"?movejump=1&movejump_page={page}&pagestamp={pagestamp}"
                )
            resp = self.session.get(url, headers=ajax_headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            rows = soup.select(".rowContainerHolder")
            if not rows:
                break

            for row in rows:
                link = row.select_one(".rowLabel a")
                if link is None:
                    continue
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not href or not title:
                    continue

                id_match = ID_RE.search(href)
                posting_id = id_match.group(1) if id_match else href
                if posting_id in seen_ids:
                    continue
                seen_ids.add(posting_id)

                location_el = row.select_one(".codelist5value_vacancyColumn")
                location = location_el.get_text(strip=True) if location_el else ""

                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location=location,
                        url=urljoin(list_url, href),
                        posting_id=posting_id,
                        ats=self.ats_name,
                    )
                )

            page += 1

        return postings
