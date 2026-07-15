"""Dentons career-search adapter.

Dentons runs a bespoke ASP.NET .asmx web service
(www.dentons.com/DentonsServices/career.asmx/GetJobsByState) rather than
a third-party ATS -- confirmed via live browser network capture: real
JSON back (id/title/narrative/link per posting, with a genuine per-job
URL) with no auth or session cookies required (all context is carried in
the query string itself: contextItem/contextItemUrl/contextLanguage/
contextSite). Paginated via pageNumber/pageSize; sweeps pageNumber
upward until an empty results array comes back.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter

PAGE_SIZE = 20


class DentonsCareerAdapter(Adapter):
    ats_name = "Dentons Career Search"

    def fetch(self) -> list[Posting]:
        api_url = self.config["api_url"]
        context_item = self.config["context_item"]
        context_url = self.config["context_url"]

        postings: list[Posting] = []
        page_number = 1
        while True:
            params = {
                "officeID": "",
                "pageSize": PAGE_SIZE,
                "pageNumber": page_number,
                "contextItem": context_item,
                "contextItemUrl": context_url,
                "contextLanguage": "en",
                "contextSite": "dentons",
            }
            resp = self.session.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for job in results:
                posting_id = job.get("id", "")
                title = job.get("title", "")
                if not posting_id or not title:
                    continue
                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location="",
                        url=job.get("link", ""),
                        posting_id=posting_id,
                        ats=self.ats_name,
                        description=job.get("narrative", ""),
                    )
                )

            page_number += 1

        return postings
