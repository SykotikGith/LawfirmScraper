"""UKG/UltiPro Recruiting (UltiPro JobBoard) adapter.

UltiPro career sites (recruiting.ultipro.com/<CompanyCode>/JobBoard/<BoardId>/)
are Knockout.js-rendered pages with no job data in static HTML -- there is
no classic server-rendered link list here (that was an earlier, wrong
assumption). The real job data comes from a JSON search endpoint at
<board_url>/JobBoardView/LoadSearchResults, POSTed with
{"opportunitySearch": {"Text": "", "Skip": N, "Take": 20}}.

CONFIRMED via live probing (Akerman, July 2026): the server hard-caps page
size to 20 regardless of the requested Take value, and PageNumber/PageSize
params (the initial guess) are silently ignored -- pagination is purely
Skip-driven. Sweeping Skip in steps of 20 up to totalCount retrieves every
posting exactly once (verified end-to-end: 96/96 unique Ids, zero
duplicates or gaps). The per-job detail URL is
<board_url>/OpportunityDetail?opportunityId=<Id>, confirmed from the page's
own opportunityLinkUrl template.

No full job description text is available in the search response
(BriefDescription is just a copy of the title, not real body text) -- work-
arrangement detection for this adapter relies on location text alone, same
as Workday/Circa Works/ApplicantStack. Each opportunity does carry
JobLocationType/OpportunityType integer fields that might encode a
remote/hybrid/onsite signal directly, but their enum mapping wasn't
confirmed (only one plainly-onsite sample was seen) -- worth revisiting if
this firm's detection accuracy needs improvement later.
"""
from __future__ import annotations

from ..models import Posting
from .base import Adapter

TAKE = 20  # server hard-caps page size to this regardless of the requested value


class UltiProAdapter(Adapter):
    ats_name = "UltiPro"

    def fetch(self) -> list[Posting]:
        board_url = self.config["board_url"].rstrip("/")
        search_url = f"{board_url}/JobBoardView/LoadSearchResults"

        postings: list[Posting] = []
        skip = 0
        total = None
        while True:
            body = {"opportunitySearch": {"Text": "", "Skip": skip, "Take": TAKE}}
            resp = self.session.post(search_url, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            opportunities = data.get("opportunities", [])
            if not opportunities:
                break

            for opp in opportunities:
                posting_id = opp.get("Id", "")
                title = opp.get("Title", "")
                if not posting_id or not title:
                    continue
                location = self._location_text(opp.get("Locations") or [])
                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location=location,
                        url=f"{board_url}/OpportunityDetail?opportunityId={posting_id}",
                        posting_id=posting_id,
                        ats=self.ats_name,
                    )
                )

            if total is None:
                total = data.get("totalCount") or 0
            skip += TAKE
            if skip >= total:
                break

        return postings

    @staticmethod
    def _location_text(locations: list[dict]) -> str:
        parts = []
        for loc in locations:
            address = loc.get("Address") or {}
            city = address.get("City")
            state = (address.get("State") or {}).get("Code")
            if city and state:
                parts.append(f"{city}, {state}")
            elif loc.get("LocalizedDescription"):
                parts.append(loc["LocalizedDescription"])
        return "; ".join(parts)
