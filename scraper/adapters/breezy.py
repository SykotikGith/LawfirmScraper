"""Breezy HR adapter.

Breezy HR career sites expose a public, unauthenticated JSON endpoint at
https://<subdomain>.breezy.hr/json returning every open posting directly
in one flat array -- no pagination, no session priming needed. Confirmed
via live probing: id, friendly_id, name (title), url (a real per-job
link), location.name / location.is_remote, department, and company.name
are all present. No description text in the list response itself (would
need a second request per job to the position detail page), so
work-arrangement detection here relies on location text alone -- is_remote
gets folded into the location string as a leading "Remote" so
work_arrangement.py's plain substring match picks it up.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter


class BreezyAdapter(Adapter):
    ats_name = "Breezy HR"

    def fetch(self) -> list[Posting]:
        json_url = self.config["json_url"]
        resp = self.session.get(json_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        postings: list[Posting] = []
        for item in data:
            posting_id = item.get("id", "")
            title = item.get("name", "")
            if not posting_id or not title:
                continue

            location_info = item.get("location") or {}
            location = location_info.get("name", "")
            if location_info.get("is_remote"):
                location = f"Remote ({location})" if location else "Remote"

            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=item.get("url", ""),
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
