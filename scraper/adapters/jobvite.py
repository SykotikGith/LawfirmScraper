"""Jobvite adapter.

Jobvite career sites (jobs.jobvite.com/<company>/) look like a client-side
JS app from the page shell (CloudFront-hosted app.js bundle, small
initial payload) but CONFIRMED via live probing (Davis Wright Tremaine,
July 2026): the job list itself is server-rendered in a plain HTML table
regardless -- no separate API call or JS execution needed. Each row has
a title link (td.jv-job-list-name a, href like /<company>/job/<id>) and
a location cell (td.jv-job-list-location) whose text has stray
punctuation spacing from an inline <span>, cleaned up before use.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

_WHITESPACE_RE = re.compile(r"\s+")


class JobviteAdapter(Adapter):
    ats_name = "Jobvite"

    def fetch(self) -> list[Posting]:
        board_url = self.config["board_url"]
        resp = self.session.get(board_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        for link in soup.select("td.jv-job-list-name a"):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue

            url = urljoin(board_url, href)
            posting_id = href.rstrip("/").rsplit("/", 1)[-1]

            location = ""
            row = link.find_parent("tr")
            if row is not None:
                loc_cell = row.select_one("td.jv-job-list-location")
                if loc_cell is not None:
                    location = _WHITESPACE_RE.sub(" ", loc_cell.get_text(" ", strip=True)).replace(" ,", ",")

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
