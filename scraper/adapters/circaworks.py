"""Circa Works (LocalJobNetwork) adapter.

Circa Works job boards render job links as javascript: pseudo-protocol
hrefs (`javascript: self.popup('/j/t-Title-e-Employer-l-Location-jobs-
jNNNNNNNN.html?pbid=...', ...)`) rather than plain <a href> URLs. The
real path -- and conveniently, the title/employer/location -- is
encoded directly in the popup() call's URL slug, so we regex it out
rather than depend on the anchor's visible text (unverified, and
unnecessary given the slug already has everything).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

POPUP_PATH_RE = re.compile(r"self\.popup\('([^']+)'")
SLUG_RE = re.compile(r"/j/t-(.+?)-e-(.+?)-l-(.+?)-jobs-j(\d+)\.html")


class CircaWorksAdapter(Adapter):
    ats_name = "Circa Works"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]
        resp = self.session.get(list_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        postings: list[Posting] = []
        seen_ids: set[str] = set()
        for link in soup.select("a[href^='javascript']"):
            href = link.get("href", "")
            popup_match = POPUP_PATH_RE.search(href)
            if not popup_match:
                continue
            path = popup_match.group(1)

            slug_match = SLUG_RE.search(path)
            if not slug_match:
                continue
            title_slug, _employer_slug, location_slug, job_id = slug_match.groups()
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = title_slug.replace("-", " ")
            location = location_slug.replace("-", " ")
            url = f"https://employer.circaworks.com{path}"

            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=url,
                    posting_id=job_id,
                    ats=self.ats_name,
                )
            )
        return postings
