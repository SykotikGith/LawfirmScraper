"""viGlobal (viRecruit) adapter.

viGlobal job boards render all postings directly in a server-side
ASP.NET GridView table (id=contentPlaceHolder_gridviewList by default)
-- no separate API call needed. Each cell concatenates title/office/
group/dates/full-description with no separators once rendered as plain
text (e.g. "AssistantOfficeDallasGroupAssistant (Litigation)Date
PostedMar 03, 2026Application DeadlineJan 01, 2027<full description>"),
so the structured fields are regexed out rather than selected via
child-element CSS selectors (not reliably distinguishable in this
markup).

Job "Apply" controls are ASP.NET postback LinkButtons
(javascript:__doPostBack(...)), not real navigable URLs, so there's no
per-job URL to link to -- every posting points at the shared listing
page, and posting_id is derived from title+office+group instead of a
URL or numeric ID.
"""
from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

ROW_TEXT_RE = re.compile(
    r"^(?P<title>.+?)Office(?P<office>.+?)Group(?P<group>.+?)"
    r"Date Posted(?P<date>[A-Za-z]+ \d{1,2}, \d{4})Application Deadline"
)


class ViGlobalAdapter(Adapter):
    ats_name = "viGlobal"

    def fetch(self) -> list[Posting]:
        list_url = self.config["list_url"]
        table_id = self.config.get("table_id", "contentPlaceHolder_gridviewList")

        resp = self.session.get(list_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", id=table_id)
        if table is None:
            return []

        postings: list[Posting] = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            text = cells[0].get_text(strip=True)
            match = ROW_TEXT_RE.match(text)
            if not match:
                continue

            title = match.group("title").strip()
            office = match.group("office").strip()
            group = match.group("group").strip()
            if not title:
                continue

            posting_id = hashlib.sha1(f"{title}|{office}|{group}".encode()).hexdigest()[:12]
            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=office,
                    url=list_url,
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
