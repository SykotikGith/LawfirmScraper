"""Oracle Recruiting Cloud / Taleo adapter.

Oracle Recruiting Cloud exposes a REST endpoint under /hcmRestApi/resources/
that returns job requisitions as JSON. The exact host and siteNumber are
tenant-specific and must be supplied via config.

Requisitions carry a structured work-arrangement signal --
`WorkplaceTypeCode` (e.g. "ORA_HYBRID") and often a human-readable
`WorkplaceType` -- plus free-text description fields. We fold all of
these into `description` so `work_arrangement.detect_work_arrangement`
can pick them up; the underscore in e.g. "ORA_HYBRID" is replaced with a
space first so `\bhybrid\b` actually matches it (underscore counts as a
word character, so "ORA_HYBRID" alone wouldn't have a boundary before
"HYBRID").
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter


class OracleRecruitingAdapter(Adapter):
    ats_name = "Oracle Recruiting Cloud"

    def fetch(self) -> list[Posting]:
        api_url = self.config["api_url"]
        job_url_template = self.config["job_url_template"]  # must contain {id}

        resp = self.session.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [{}])
        requisitions = items[0].get("requisitionList", []) if items else []

        postings: list[Posting] = []
        for req in requisitions:
            posting_id = str(req.get("Id") or req.get("ReqId") or "")
            title = req.get("Title", "")
            location = req.get("PrimaryLocation", "")
            if not posting_id or not title:
                continue
            description = " ".join(
                part
                for part in [
                    req.get("WorkplaceType") or "",
                    (req.get("WorkplaceTypeCode") or "").replace("_", " "),
                    req.get("ShortDescriptionStr") or "",
                    req.get("ExternalQualificationsStr") or "",
                    req.get("ExternalResponsibilitiesStr") or "",
                ]
                if part
            )
            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=job_url_template.format(id=posting_id),
                    posting_id=posting_id,
                    ats=self.ats_name,
                    description=description,
                )
            )
        return postings
