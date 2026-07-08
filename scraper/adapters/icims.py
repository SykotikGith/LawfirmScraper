"""iCIMS adapter.

iCIMS-hosted career sites (careers-<tenant>.icims.com) render a server-side
job search results page whose job links follow the pattern
/jobs/<id>/<slug>/job. We fetch the search page and parse those anchors —
iCIMS does not expose a stable public JSON API for external scraping.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

JOB_LINK_RE = re.compile(r"/jobs/(\d+)/")


class ICIMSBlockedError(RuntimeError):
    """Raised when the iCIMS tenant is behind an unsolvable AWS WAF bot challenge."""


class ICIMSAdapter(Adapter):
    ats_name = "iCIMS"

    def fetch(self) -> list[Posting]:
        tenant = self.config["tenant"]
        search_url = self.config.get(
            "search_url",
            f"https://careers-{tenant}.icims.com/jobs/search?pr=0&in_iframe=1",
        )
        resp = self.session.get(search_url, timeout=30)
        if "Human Verification" in resp.text or "awsWafCookieDomainList" in resp.text:
            raise ICIMSBlockedError(
                f"{tenant}: iCIMS tenant is behind an AWS WAF bot challenge -- not scrapable "
                "with a plain HTTP client. Needs browser automation (Playwright) or a manual "
                "check."
            )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        seen_ids: set[str] = set()
        for link in soup.select("a[href*='/jobs/']"):
            href = link.get("href", "")
            match = JOB_LINK_RE.search(href)
            if not match:
                continue
            posting_id = match.group(1)
            if posting_id in seen_ids:
                continue
            seen_ids.add(posting_id)

            title = link.get_text(strip=True)
            if not title:
                continue
            url = href if href.startswith("http") else f"https://careers-{tenant}.icims.com{href}"

            location = ""
            row = link.find_parent(["tr", "li", "div"])
            if row is not None:
                loc_el = row.select_one(".location, .job-location, .iCIMS_JobLocation")
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
