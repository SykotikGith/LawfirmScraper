"""Kirkland & Ellis adapter -- genuine runtime PlaywrightAdapter.

staffjobsus.kirkland.com is a Talemetry Career Sites product (Cornerstone)
gated by a Cloudflare JS bot-management challenge on plain HTTP -- but a
genuine headless-Chromium session passes it. Two URL-shape quirks
confirmed via extensive live probing (10 diagnostic rounds):

1. /jobs/search/ (WITH a trailing slash) renders the real, unfiltered,
   all-155-jobs listing cleanly. /jobs/search (NO trailing slash) --
   including every real pagination link on the site, which are all
   built as /jobs/search?page=N -- hits a HARD Cloudflare challenge
   ("Just a moment...", "Performing security verification") that even a
   real browser session with valid cookies from the trailing-slash page
   cannot get past (confirmed by clicking the real in-page "NEXT" link,
   not just guessing a URL). This site's Cloudflare rule appears to key
   on the exact request path including the trailing slash.

2. That means only page 1 (25 of the ~155 total real postings) is
   reachable at all -- not a partial/lazy result, a confirmed hard
   ceiling. Per the project's "don't force it" instruction for Category
   2 (bot-protection) firms, this ships page-1-only coverage rather than
   spending more time on the pagination block. Same category of gap as
   Akin Gump's already-documented single-page limitation.

Job rows have no clean per-row DOM container found in probing (title
lives in an <h2><a> with a sibling <sup>NEW</sup> badge for recent
postings; category/location/date columns' container wasn't isolated) --
instead of chasing that markup further, title/category/location/date are
parsed from the page's own rendered visible text (page.inner_text),
which repeats a reliable 4-line-per-job pattern confirmed against real
output, and matched positionally (same top-to-bottom DOM order) against
the real per-job <a href> links queried separately for real detail-page
URLs and IDs.
"""
from __future__ import annotations

import hashlib
import re

from ..models import Posting
from .playwright_base import PlaywrightAdapter

NAV_WAIT_MS = 6_000
ROW_RE = re.compile(
    r"(?P<title>[^\n]+?)\n(?P<category>[^\n]+)\xa0\n(?P<location>[^\n]+)\xa0\n(?P<date>[^\n]+)\xa0\n"
)
JOB_ID_RE = re.compile(r"kirkland\.com/jobs/(\d+)-")


class KirklandAdapter(PlaywrightAdapter):
    ats_name = "Talemetry (Kirkland & Ellis)"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]

        with self._browser_page() as page:
            page.goto(list_url, wait_until="load")
            page.wait_for_timeout(NAV_WAIT_MS)

            links = page.query_selector_all("a[href*='staffjobsus.kirkland.com/jobs/']")
            hrefs = [link.get_attribute("href") or "" for link in links]

            body = page.inner_text("body")
            idx = body.find("Job Title")
            rows = list(ROW_RE.finditer(body[idx:])) if idx != -1 else []

            postings: list[Posting] = []
            for href, row in zip(hrefs, rows):
                title = re.sub(r"\s+NEW$", "", row.group("title")).strip()
                if not title or not href:
                    continue
                location = row.group("location").strip()

                job_id_match = JOB_ID_RE.search(href)
                posting_id = (
                    job_id_match.group(1)
                    if job_id_match
                    else hashlib.sha1(f"{title}|{location}".encode()).hexdigest()[:12]
                )
                postings.append(
                    Posting(
                        firm=self.firm,
                        title=title,
                        location=location,
                        url=href,
                        posting_id=posting_id,
                        ats=self.ats_name,
                    )
                )

        return postings
