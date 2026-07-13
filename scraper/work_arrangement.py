"""Remote/hybrid/onsite detection for scraped postings.

Signals, checked in this order (first match wins):
  hybrid  -- "hybrid" or "N day(s) ... office/onsite"-style partial
             in-office language in location or description
  remote  -- "Remote"/"Virtual"/"Nationwide" in location, or explicit
             fully-remote/work-from-home language in description
  onsite  -- explicit contradicting language only: location says
             "onsite"/"on-site" directly, or description explicitly rules
             out remote ("on-site required", "must work from office", "no
             remote option", etc.)
  unclear -- none of the above. This is the default for a plain city/office
             location with no explicit language either way -- silence
             about work arrangement means "verify," not "confirmed
             onsite." A bare "Chicago, IL" location is common for postings
             that are actually hybrid or remote-eligible but just don't
             say so in the location field.

Hybrid is checked ahead of remote because it's the more specific claim --
a posting that says "hybrid, 3 days a week in office" shouldn't read as
Remote just because boilerplate benefits text elsewhere says "remote work
considered".

Most adapters only have `location` to go on (no per-job description text
without an extra HTTP request per posting) -- `description` is "" for
those, and detection still works, it just leans on location alone and
falls to "unclear" more often for lack of any description text to search
for explicit onsite/remote/hybrid language. That's a known, deliberate
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

ONSITE_LOCATION_RE = re.compile(r"\bon[-\s]?site\b", re.IGNORECASE)

# Explicit language that rules out remote/hybrid entirely -- a plain city
# name is NOT enough on its own (see module docstring).
ONSITE_DESC_PATTERNS = [
    re.compile(rf"\b{p}\b", re.IGNORECASE)
    for p in [
        "on-?site required",
        "must work from (?:the )?office",
        "must work in(?:-| )?office",
        "no remote option",
        "no remote work",
        "not a remote position",
        "not eligible for remote",
        "in-?office position",
        "fully on-?site",
        "100% on-?site",
        "on-?site only",
        "in-person only",
        "required to work on-?site",
        "required to be on-?site",
        "must be on-?site",
    ]
]


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

    onsite_signals = []
    if ONSITE_LOCATION_RE.search(location):
        onsite_signals.append('location contains "onsite"/"on-site"')
    for pattern in ONSITE_DESC_PATTERNS:
        match = pattern.search(description)
        if match:
            onsite_signals.append(f'description contains "{match.group(0)}"')
    if onsite_signals:
        return WorkArrangement(status="onsite", signals=onsite_signals)

    fallback_signal = "no explicit remote/hybrid/onsite language found"
    if location.strip():
        fallback_signal += f' (location: "{location.strip()}", not treated as a signal on its own)'
    return WorkArrangement(status="unclear", signals=[fallback_signal])
