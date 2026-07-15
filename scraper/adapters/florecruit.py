"""FloRecruit adapter.

FloRecruit career sites (Next.js front-end, e.g. florecruit.com/v2/app/
<org>/jobs) render results client-side via a GraphQL call whose query
shape wasn't discoverable from static probing -- but there's also a much
simpler public REST endpoint that returns everything directly:
https://florecruit.com/api/v2/public-jobs/<org>/career-page-jobs
Confirmed via live browser network capture (Sheppard Mullin): 16 real
postings in one response, no pagination needed, no auth/session required
(works from a fresh unauthenticated request, not just from within an
established browser session).

No confirmed real per-job URL pattern yet -- job records don't include a
detail-page URL, and the "extension" field looks like an opaque encoded
slug rather than something safe to guess a URL from. Falls back to the
firm's list_url for now.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter


class FloRecruitAdapter(Adapter):
    ats_name = "FloRecruit"

    def fetch(self) -> list[Posting]:
        api_url = self.config["api_url"]
        list_url = self.config.get("list_url", api_url)

        resp = self.session.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        postings: list[Posting] = []
        for job in data:
            posting_id = str(job.get("id", ""))
            title = job.get("title", "")
            if not posting_id or not title:
                continue

            offices = job.get("jobOffices") or []
            location = "; ".join(o.get("name", "") for o in offices if o.get("name"))

            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=list_url,
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
