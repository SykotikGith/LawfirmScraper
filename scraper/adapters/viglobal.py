"""viGlobal (viRecruit) adapter.

viGlobal job boards render all postings directly in a server-side
ASP.NET GridView table (id=contentPlaceHolder_gridviewList by default)
-- no separate API call needed, but the row markup varies by tenant
(confirmed two shapes so far):

1. O'Melveny & Myers' shape: each cell concatenates title/office/group/
   dates/full-description with no separators once rendered as plain text
   (e.g. "AssistantOfficeDallasGroupAssistant (Litigation)Date
   PostedMar 03, 2026Application DeadlineJan 01, 2027<full description>"),
   so the fields are regexed out of that blob.
2. Bryan Cave Leighton Paisner's shape: real structured tags --
   <h4>{title}</h4> and <h5>{label} <span>{value}</span></h5> per field
   (Office/Practice Area/Date Posted/Application Deadline). Note
   BeautifulSoup's get_text(strip=True) strips each text fragment BEFORE
   joining with an empty separator, so "Office " + "Atlanta" comes out as
   "OfficeAtlanta" with no space -- label detection uses a prefix match
   against the mashed string rather than trying to split it apart, and
   the real value is read from the <span> directly. This template's
   description div is always empty in server-rendered HTML
   (data-vi-filter="detail", populated client-side after load) --
   description stays "" for this shape, same as adapters with no
   description text available at all.

Both shapes are tried per row, structured-tags first (and also cover a
third, Vinson & Elkins' self-hosted deployment -- same <h4>{title}</h4>
structure but no <h5> office/practice fields at all, so office/group come
back empty; location sometimes ends up embedded directly in the title
text instead, e.g. "Billing Coordinator - Austin, Dallas, Houston").

Job "Apply" controls are ASP.NET postback LinkButtons
(javascript:__doPostBack(...)) for O'Melveny and Bryan Cave -- not real
navigable URLs, so those postings point at the shared listing page and
posting_id is derived from title+office+group. Vinson & Elkins' shape is
different: its "More Info" control is a real <a href="ReJobView.aspx?
...&JobID=N"> link, so when a non-javascript href is found in the row we
use that (resolved against list_url) as the real per-job URL, and pull
the numeric JobID out of it for posting_id instead of hashing.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Posting
from .base import Adapter

JOB_ID_RE = re.compile(r"[?&]JobID=(\d+)", re.IGNORECASE)

ROW_TEXT_RE = re.compile(
    r"^(?P<title>.+?)Office(?P<office>.+?)Group(?P<group>.+?)"
    r"Date Posted(?P<date>[A-Za-z]+ \d{1,2}, \d{4})Application Deadline"
)


def _parse_structured_row(row) -> tuple[str, str, str, str, str | None] | None:
    """Bryan Cave Leighton Paisner's <h4>/<h5><span> shape, and Vinson &
    Elkins' <h4>-only variant. Returns (title, office, group, description,
    detail_url) or None if this row isn't in that shape at all (h4
    missing). detail_url is the row's own non-javascript href if one
    exists (Vinson & Elkins), else None (Bryan Cave/O'Melveny postbacks)."""
    h4 = row.find("h4")
    if h4 is None:
        return None
    title = h4.get_text(strip=True)
    if not title:
        return None

    office = ""
    group = ""
    for h5 in row.find_all("h5"):
        span = h5.find("span")
        if span is None:
            continue
        label = h5.get_text(strip=True)  # mashed, e.g. "OfficeAtlanta" -- prefix-match only
        value = span.get_text(strip=True)
        if label.startswith("Office"):
            office = value
        elif label.startswith("Practice") or label.startswith("Group"):
            group = value

    detail_url = None
    for a in row.find_all("a", href=True):
        href = a["href"]
        if href and not href.lower().startswith("javascript:"):
            detail_url = href
            break

    return title, office, group, "", detail_url


def _parse_text_blob_row(cell_text: str) -> tuple[str, str, str, str, str | None] | None:
    """O'Melveny & Myers' concatenated-plain-text shape."""
    match = ROW_TEXT_RE.match(cell_text)
    if not match:
        return None
    title = match.group("title").strip()
    if not title:
        return None
    office = match.group("office").strip()
    group = match.group("group").strip()
    # Full description trails immediately after the regex match -- already
    # fetched, just needs slicing off rather than a second per-job request.
    description = cell_text[match.end():].strip()
    return title, office, group, description, None


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

            parsed = _parse_structured_row(row)
            if parsed is None:
                parsed = _parse_text_blob_row(cells[0].get_text(strip=True))
            if parsed is None:
                continue
            title, office, group, description, detail_url = parsed

            url = urljoin(list_url, detail_url) if detail_url else list_url
            job_id_match = JOB_ID_RE.search(detail_url) if detail_url else None
            posting_id = (
                job_id_match.group(1)
                if job_id_match
                else hashlib.sha1(f"{title}|{office}|{group}".encode()).hexdigest()[:12]
            )
            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=office,
                    url=url,
                    posting_id=posting_id,
                    ats=self.ats_name,
                    description=description,
                )
            )
        return postings
