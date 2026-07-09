"""UKG/UltiPro Recruiting (UltiPro JobBoard) adapter.

Classic-template UltiPro career sites
(recruiting.ultipro.com/<CompanyCode>/JobBoard/<BoardId>/) list postings as
plain <a href="OpportunityDetail.aspx?opportunityId=...">Title</a> links,
server-rendered directly into the page -- no separate API call needed. The
newer Angular-based JobBoard template is pure client-side JS instead and
won't have any of this in static HTML; if this adapter returns nothing for
a given tenant, that's the first thing to check before assuming the board
URL is wrong.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

OPPORTUNITY_ID_RE = re.compile(r"opportunityId=([^&]+)", re.IGNORECASE)


class UltiProAdapter(Adapter):
    ats_name = "UltiPro"

    def fetch(self) -> list[Posting]:
        board_url = self.config["board_url"]
        resp = self.session.get(board_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        seen_ids: set[str] = set()
        for link in soup.select("a[href*='OpportunityDetail.aspx']"):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue

            id_match = OPPORTUNITY_ID_RE.search(href)
            posting_id = id_match.group(1) if id_match else href
            if posting_id in seen_ids:
                continue
            seen_ids.add(posting_id)

            url = urljoin(board_url, href)

            location = ""
            row = link.find_parent(["tr", "li", "div"])
            if row is not None:
                loc_el = row.select_one(".location, .job-location, .opportunity-location")
                if loc_el:
                    location = loc_el.get_text(strip=True)

            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=url,
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
