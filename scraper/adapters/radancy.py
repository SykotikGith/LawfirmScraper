"""Radancy "Attract" career-site adapter (platform name inferred from a
"ccc.attract.portal.url" key found inside the response's own metadata --
not independently confirmed via vendor documentation, but kept as a
working label).

Exposes a public, unauthenticated JSON endpoint at <domain>/api/jobs
returning {"jobs": [{"data": {...}}], "totalCount": N, ...}. Pagination is
page-number-based (?page=N, 1-indexed) -- start/offset/num params are all
silently ignored, and the server hard-caps each page to 10 jobs regardless
of what's requested. Confirmed via live probing (Ogletree Deakins):
totalCount=148, page=15 returns the trailing 8 jobs, page=16 returns
empty -- sweep pages from 1 until an empty page comes back.

The underlying ATS is actually iCIMS (each job's own ats_code field says
so), but this wrapper endpoint isn't behind the WAF challenge that blocks
iCIMS everywhere else in this project -- a clean path to the same data.
meta_data.canonical_url is a nicer firm-hosted link than apply_url (which
redirects straight into an iCIMS login/apply flow), so that's preferred
when present. qualifications/responsibilities are both real HTML body
text already present in the list response at no extra request cost, so
they're folded into description the same way Oracle Recruiting Cloud's
adapter does.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter


class RadancyAdapter(Adapter):
    ats_name = "Radancy"

    def fetch(self) -> list[Posting]:
        api_url = self.config["api_url"]

        postings: list[Posting] = []
        page = 1
        while True:
            resp = self.session.get(api_url, params={"page": page}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])
            if not jobs:
                break

            for job in jobs:
                fields = job.get("data", {})
                posting_id = fields.get("req_id") or fields.get("slug", "")
                title = fields.get("title", "")
                if not posting_id or not title:
                    continue

                location = fields.get("full_location") or fields.get("location_name", "")
                meta = fields.get("meta_data") or {}
                url = meta.get("canonical_url") or fields.get("apply_url", "")
                description = " ".join(
                    part
                    for part in [fields.get("qualifications") or "", fields.get("responsibilities") or ""]
                    if part
                )

                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location=location,
                        url=url,
                        posting_id=posting_id,
                        ats=self.ats_name,
                        description=description,
                    )
                )

            page += 1

        return postings
