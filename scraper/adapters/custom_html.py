"""Generic HTML-scraping adapter for firms with a bespoke careers page.

Config keys:
  list_url: page to fetch
  link_selector: CSS selector matching each job's <a> title link
  location_selector (optional): CSS selector, relative to the link's row, for location text
"""
from __future__ import annotations

import hashlib

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter


class CustomHTMLAdapter(Adapter):
    ats_name = "custom"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]
        link_selector = self.config["link_selector"]
        location_selector = self.config.get("location_selector")

        resp = self.session.get(list_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        for link in soup.select(link_selector):
            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue
            url = href if href.startswith("http") else f"{list_url.rstrip('/')}{href}"
            posting_id = hashlib.sha1(url.encode()).hexdigest()[:12]

            location = ""
            if location_selector:
                row = link.find_parent(["tr", "li", "div"])
                if row is not None:
                    loc_el = row.select_one(location_selector)
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
