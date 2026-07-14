"""AEM (Adobe Experience Manager) careers-search adapter.

Some firms run a bespoke career-search feature on their AEM-based
marketing site rather than pointing straight at a third-party ATS. The
page embeds a small JSON config (a Sling servlet reference, e.g.
{"careerSearchPath": "/bin/careersSearch", "type": "getCareers", ...})
that exposes a clean, unauthenticated GET endpoint returning
{"Total": N, "OpenPositions": [...]} directly -- no pagination, confirmed
via live probing (Dechert) that all N postings come back in one response
regardless of any position/positionType filter param (both accepted and
silently ignored, so this adapter doesn't bother sending one).

The underlying data can be proxied from a real third-party ATS behind the
scenes (Dechert's Url field for each posting points at a viGlobal-hosted
apply page) but the AEM wrapper endpoint itself has no bot protection,
unlike hitting that backend directly.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter


class AEMCareerSearchAdapter(Adapter):
    ats_name = "AEM Career Search"

    def fetch(self) -> list[Posting]:
        api_url = self.config["api_url"]
        resp = self.session.get(api_url, params={"type": "getCareers"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        postings: list[Posting] = []
        for job in data.get("OpenPositions", []):
            posting_id = str(job.get("ID", ""))
            title = job.get("Title", "")
            if not posting_id or not title:
                continue

            locations = job.get("Locations") or []
            location = "; ".join(loc.get("Location", "") for loc in locations if loc.get("Location"))

            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=job.get("Url", ""),
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
