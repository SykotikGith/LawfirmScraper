"""Paul Weiss adapter -- classic Taleo Enterprise career section.

paulweiss.taleo.net/careersection/ex/jobsearch.ftl serves the search
FORM only; results only populate after a self-submitting POST triggered
by clicking Search, with no discoverable AJAX/REST endpoint -- confirmed
across several diagnostic rounds. This uses a genuine runtime
PlaywrightAdapter (like Venable) to click Search and read the rendered
rows, rather than trying to replay the POST directly.

Each rendered row (<tr>) has an id-suffix'd title link
(a[id*='reqTitleLinkAction']) whose visible text is the job title, and
its own innerText -- e.g. "Business Services Assistant\xa0\nRequisition
ID:\xa026000223\nWork Locations:\xa0United States-CA-San
Francisco\nSchedule:\xa0Full-time\nJob Posting:\xa0Jun 29,
2026\nApply|Add to My Job Cart" -- carries the requisition ID and work
location, extracted by regex. There's no real per-job href in the
listing (postback-only JS, same as viGlobal's O'Melveny/Bryan Cave
tenants), but classic Taleo Enterprise sites serve a real, plain,
GET-able detail page at jobdetail.ftl?job=<requisitionID> -- confirmed
live for requisition 26000223 -- so that's used as the per-posting URL
and posting_id, instead of falling back to the list page like Venable
has to.
"""
from __future__ import annotations

import re

from ..models import Posting
from .playwright_base import PlaywrightAdapter

NAV_WAIT_MS = 4_000
REQ_ID_RE = re.compile(r"Requisition ID:\xa0(\S+)")
LOC_RE = re.compile(r"Work Locations:\xa0([^\n]+)")


class PaulWeissAdapter(PlaywrightAdapter):
    ats_name = "Taleo Enterprise (Paul Weiss)"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]
        detail_url_template = self.config.get(
            "detail_url_template",
            "https://paulweiss.taleo.net/careersection/ex/jobdetail.ftl?job={job_id}",
        )

        with self._browser_page() as page:
            page.goto(list_url, wait_until="load")
            page.wait_for_timeout(NAV_WAIT_MS)
            try:
                page.get_by_role("button", name=re.compile("search", re.I)).first.click(timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(NAV_WAIT_MS)

            title_links = page.query_selector_all("a[id*='reqTitleLinkAction']")
            postings: list[Posting] = []
            for link in title_links:
                title = link.inner_text().strip()
                if not title:
                    continue

                row = link.evaluate_handle("el => el.closest('tr')")
                row_text = row.evaluate("el => el ? el.innerText : ''") or ""

                req_match = REQ_ID_RE.search(row_text)
                if not req_match:
                    continue
                job_id = req_match.group(1)

                loc_match = LOC_RE.search(row_text)
                location = loc_match.group(1).strip() if loc_match else ""

                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location=location,
                        url=detail_url_template.format(job_id=job_id),
                        posting_id=job_id,
                        ats=self.ats_name,
                    )
                )

        return postings
