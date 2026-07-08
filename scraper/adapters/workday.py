"""Workday adapter.

Workday-hosted career sites expose a JSON search API at
https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
which we POST an empty search against and page through with limit/offset.

Confirmed via live probing: `total` is only reliably reported on the
*first* page of a search -- subsequent pages can report total=0 even
though they keep returning genuinely different (not stale/duplicate)
results. So we capture total once, from the first response, and use
jobPostings-empty as the real stopping condition, capped by a safety
limit derived from that first total. We also prime the session with a
GET to the HTML careers page first, matching what a browser does and
what worked in testing, before hitting the JSON API.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter

PAGE_SIZE = 20
MAX_PAGES_FALLBACK = 50  # safety cap if the first page's total is missing/zero


class WorkdayAdapter(Adapter):
    ats_name = "Workday"

    def fetch(self) -> list[Posting]:
        tenant = self.config["tenant"]
        wd = self.config.get("wd", "wd1")
        site = self.config["site"]
        api_url = self.config.get(
            "api_url",
            f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
        )
        base_job_url = f"https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}"

        # Prime the session (cookies) with a normal page load first.
        self.session.get(f"https://{tenant}.{wd}.myworkdayjobs.com/{site}", timeout=30)

        postings: list[Posting] = []
        offset = 0
        total = None
        while True:
            body = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""}
            resp = self.session.post(api_url, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            job_postings = data.get("jobPostings", [])
            if not job_postings:
                break

            for job in job_postings:
                external_path = job.get("externalPath", "")
                posting_id = job.get("bulletFields", [None])[0] or external_path
                postings.append(
                    Posting(
                        firm=self.firm,
                        title=job.get("title", ""),
                        location=job.get("locationsText", ""),
                        url=f"{base_job_url}{external_path}",
                        posting_id=posting_id,
                        ats=self.ats_name,
                    )
                )

            if total is None:
                total = data.get("total") or 0

            offset += PAGE_SIZE
            page_limit = total if total else PAGE_SIZE * MAX_PAGES_FALLBACK
            if offset >= page_limit:
                break

        return postings
