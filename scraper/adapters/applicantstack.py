"""ApplicantStack adapter.

ApplicantStack job boards are server-rendered HTML lists. We fetch the
public job board page and parse job title links.
"""
from __future__ import annotations

import hashlib

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter


class ApplicantStackAdapter(Adapter):
    ats_name = "ApplicantStack"

    def fetch(self) -> list[Posting]:
        board_url = self.config["board_url"]
        resp = self.session.get(board_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        link_selector = self.config.get("link_selector", "a[href*='/job/']")
        postings: list[Posting] = []
        for link in soup.select(link_selector):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue
            url = href if href.startswith("http") else f"{board_url.rstrip('/')}{href}"
            posting_id = hashlib.sha1(url.encode()).hexdigest()[:12]

            location = ""
            row = link.find_parent(["tr", "li", "div"])
            if row is not None:
                loc_el = row.select_one(".location, .job-location")
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
