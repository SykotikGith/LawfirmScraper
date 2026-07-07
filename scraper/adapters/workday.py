"""Workday adapter.

Workday-hosted career sites expose a JSON search API at
https://<tenant>.<wd>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
which we POST an empty search against and page through with limit/offset.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter

PAGE_SIZE = 20


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

        postings: list[Posting] = []
        offset = 0
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

            total = data.get("total", 0)
            offset += PAGE_SIZE
            if offset >= total:
                break

        return postings
