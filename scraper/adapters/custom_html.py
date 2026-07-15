"""Generic HTML-scraping adapter for firms with a bespoke careers page.

Config keys:
  list_url: page to fetch
  link_selector: CSS selector matching each job's <a> title link
  title_selector (optional): CSS selector, relative to the matched link, for the title
    text specifically -- needed when the link wraps more than just the title (e.g. a
    location div nested inside the same <a>, which would otherwise get mashed into the
    title via a plain get_text() on the whole link). Defaults to the link's own full text.
  location_selector (optional): CSS selector for location text. Checked first relative to
    the link itself (covers markup where location is nested inside the same <a> as the
    title), then falls back to the link's nearest tr/li/div ancestor (covers markup where
    location is a sibling cell elsewhere in the row).
"""
from __future__ import annotations

import hashlib
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter


class CustomHTMLAdapter(Adapter):
    ats_name = "custom"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]
        link_selector = self.config["link_selector"]
        title_selector = self.config.get("title_selector")
        location_selector = self.config.get("location_selector")

        resp = self.session.get(list_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        for link in soup.select(link_selector):
            href = link.get("href", "")
            if title_selector:
                title_el = link.select_one(title_selector)
                title = title_el.get_text(strip=True) if title_el else ""
            else:
                title = link.get_text(strip=True)
            if not href or not title:
                continue
            url = urljoin(list_url, href)
            posting_id = hashlib.sha1(url.encode()).hexdigest()[:12]

            location = ""
            if location_selector:
                loc_el = link.select_one(location_selector)
                if loc_el is None:
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
