"""Greenhouse adapter.

Greenhouse job boards expose a public, unauthenticated JSON API at
https://boards-api.greenhouse.io/v1/boards/<board_token>/jobs?content=true
-- no HTML scraping needed. The `?content=true` param (already in use)
also returns each job's full HTML description in a `content` field, which
we strip tags from and keep -- no extra request needed to get it.
"""
from __future__ import annotations

import re

from ..models import Posting
from .base import Adapter

_TAG_RE = re.compile(r"<[^>]+>")


class GreenhouseAdapter(Adapter):
    ats_name = "Greenhouse"

    def fetch(self) -> list[Posting]:
        board_token = self.config["board_token"]
        api_url = self.config.get(
            "api_url",
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
        )
        resp = self.session.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        postings: list[Posting] = []
        for job in data.get("jobs", []):
            posting_id = str(job.get("id", ""))
            title = job.get("title", "")
            if not posting_id or not title:
                continue
            location = (job.get("location") or {}).get("name", "")
            description = _TAG_RE.sub(" ", job.get("content") or "")
            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=job.get("absolute_url", ""),
                    posting_id=posting_id,
                    ats=self.ats_name,
                    description=description,
                )
            )
        return postings
