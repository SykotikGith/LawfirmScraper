"""Venable adapter -- the first genuine runtime PlaywrightAdapter use in
this project.

Venable's ADP myjobs career site
(myjobs.adp.com/venablebusinessprofessionalcareers/cx) renders job cards
via Angular web components (<sdf-button>) with no plain <a href> links at
all -- CustomHTMLAdapter can't handle this. The underlying REST API
(my.adp.com/.../job-requisitions/list-view) that actually supplies this
data returns real results when called from within a live browser session,
but every attempt to replay it directly (fresh context, and from within
an already-established browser session) 400'd -- something beyond
cookies gates it (likely a CSRF token or custom header), undiscovered
after 4 diagnostic rounds. Reading the rendered DOM directly sidesteps
that entirely, at the cost of needing a real browser at scrape time.

Confirmed via live probing: each job renders as a div.job-details
containing an <sdf-button aria-label=" Title "> for the title and a
.reqLocation span for location. No real per-job URL exists in the DOM
(JS-only interactive buttons, not navigable links) -- same situation as
viGlobal's postback-only tenants, so posting_id is derived from
title+location and url falls back to list_url.

UNCONFIRMED: the API response seen during discovery reported 26 total
postings, but only a handful render without interaction -- this scrolls
the page a few times first on the assumption jobs lazy-load as you
scroll (a common Angular Material pattern), but that specific behavior
wasn't independently verified. Worth checking debug_all_titles.txt after
a real run to confirm the full count comes through.
"""
from __future__ import annotations

import hashlib

from ..models import Posting
from .playwright_base import PlaywrightAdapter

NAV_WAIT_MS = 5_000
SCROLL_ATTEMPTS = 5
SCROLL_WAIT_MS = 1_500


class VenableAdapter(PlaywrightAdapter):
    ats_name = "ADP myjobs (Venable)"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]

        with self._browser_page() as page:
            page.goto(list_url, wait_until="load")
            page.wait_for_timeout(NAV_WAIT_MS)

            for _ in range(SCROLL_ATTEMPTS):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(SCROLL_WAIT_MS)

            cards = page.query_selector_all("div.job-details")
            postings: list[Posting] = []
            for card in cards:
                button = card.query_selector("sdf-button[aria-label]")
                title = (button.get_attribute("aria-label") or "").strip() if button else ""
                if not title:
                    continue

                loc_el = card.query_selector(".reqLocation")
                location = loc_el.inner_text().strip() if loc_el else ""

                posting_id = hashlib.sha1(f"{title}|{location}".encode()).hexdigest()[:12]
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
