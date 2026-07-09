"""Remote/hybrid/onsite detection for scraped postings.

Signals, checked in this order (first match wins):
  hybrid  -- "hybrid" or "N day(s) ... office/onsite"-style partial
             in-office language in location or description
  remote  -- "Remote"/"Virtual"/"Nationwide" in location, or explicit
             fully-remote/work-from-home language in description
  onsite  -- location names a single physical place and neither of the
             above signals is present
  unclear -- no location text and no remote/hybrid signal found

Hybrid is checked ahead of remote because it's the more specific claim --
a posting that says "hybrid, 3 days a week in office" shouldn't read as
Remote just because boilerplate benefits text elsewhere says "remote work
considered".

Most adapters only have `location` to go on (no per-job description text
without an extra HTTP request per posting) -- `description` is "" for
those, and detection still works, it just leans on location alone and
falls to "onsite" or "unclear" more often. That's a known, deliberate
coverage gap, not a bug.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

REMOTE_LOCATION_TERMS = ["remote", "virtual", "nationwide"]

REMOTE_DESC_PATTERNS = [
    re.compile(rf"\b{p}\b", re.IGNORECASE)
    for p in [
        "fully remote",
        "100% remote",
        "work from home",
        "work-from-home",
        "remote position",
        "remote role",
        "remote-first",
        "fully-remote",
        "wfh",
    ]
]

HYBRID_TERM_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)

# "3 days a week in office" / "in-office 2 days" / "3-4 days onsite" etc.
HYBRID_DAYS_RE = re.compile(
    r"\b\d+\s*(?:-\d+\s*)?days?\b[^.\n]{0,40}\b(?:in.?office|on.?site|in the office|per week)\b"
    r"|\b(?:in.?office|on.?site)\b[^.\n]{0,40}\b\d+\s*(?:-\d+\s*)?days?\b",
    re.IGNORECASE,
)


@dataclass
class WorkArrangement:
    status: str  # "remote" | "hybrid" | "onsite" | "unclear"
    signals: list[str] = field(default_factory=list)


def _remote_location_hit(location: str) -> str | None:
    for term in REMOTE_LOCATION_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", location, re.IGNORECASE):
            return f'location contains "{term}"'
    return None


def detect_work_arrangement(location: str, description: str = "") -> WorkArrangement:
    location = location or ""
    description = description or ""

    hybrid_signals = []
    if HYBRID_TERM_RE.search(location):
        hybrid_signals.append('location contains "hybrid"')
    if HYBRID_TERM_RE.search(description):
        hybrid_signals.append('description contains "hybrid"')
    days_match = HYBRID_DAYS_RE.search(description) or HYBRID_DAYS_RE.search(location)
    if days_match:
        hybrid_signals.append(f'partial in-office language: "{days_match.group(0).strip()}"')
    if hybrid_signals:
        return WorkArrangement(status="hybrid", signals=hybrid_signals)

    remote_signals = []
    loc_hit = _remote_location_hit(location)
    if loc_hit:
        remote_signals.append(loc_hit)
    for pattern in REMOTE_DESC_PATTERNS:
        match = pattern.search(description)
        if match:
            remote_signals.append(f'description contains "{match.group(0)}"')
    if remote_signals:
        return WorkArrangement(status="remote", signals=remote_signals)

    if location.strip():
        return WorkArrangement(
            status="onsite",
            signals=[f'single location "{location.strip()}", no remote/hybrid language'],
        )

    return WorkArrangement(
        status="unclear",
        signals=["no location text and no remote/hybrid signal found"],
    )
