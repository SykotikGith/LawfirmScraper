"""JD-required / bar-admission-required detection for scraped postings.

Runs only on postings that already passed the title-level filter
(auto_match or review tier) and the work-arrangement filter -- fetching a
full description page per posting (see main.py's `_fetch_description`) is
only affordable for that much smaller set, not every posting scraped
across all ~69 firms.

Looks for EXPLICIT "required" framing around a law degree or bar admission
-- "J.D. required", "must have a J.D.", "active bar admission required",
"licensed attorney required", etc. Deliberately does NOT flag "preferred"/
"a plus"/"nice to have" framing: every pattern here requires "required" (or
must have/hold/possess) wording specifically, so a title like "JD or other
advanced degree... a plus" simply doesn't match any pattern -- no separate
suppression logic needed, the positive patterns are just narrow enough not
to fire on optional framing in the first place.

Negation-aware: checks a short window of text immediately before each match
for a negation word ("no", "not", "never", "without") so phrasing like "no
J.D. required" isn't flagged. "Law degree not required" is also naturally
excluded by the patterns themselves -- they don't allow "not" to appear
between the degree mention and "required", so that phrasing never matches
to begin with.

Fails open like every other best-effort text filter in this project: no
description text (adapter didn't provide one and the per-posting fetch
failed, or the detail page is JS-rendered with no server-side text) means
no match is possible, so the posting stays visible rather than being
wrongly excluded. A known, deliberate coverage gap for JS-heavy detail
pages, not a bug -- same category of gap as work_arrangement.py's
per-adapter description-availability gap.

Also a known, deliberate risk in the other direction: description text is
pulled from the whole fetched page (no per-ATS "just the job description
div" selector -- that would need per-platform work well out of scope
here), so sitewide boilerplate/footer text containing one of these phrases
could theoretically cause a false-positive exclusion. Log every exclusion
(see main.py) specifically so this can be reviewed and tuned the same way
the title-level Lawyer/Attorney/Counsel exclusions were.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_NEGATION_WINDOW = 20
_NEGATION_RE = re.compile(r"\b(?:no|not|never|without)\s*$", re.IGNORECASE)

JD_REQUIRED_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"j\.?d\.?\s+(?:degree\s+)?(?:is\s+)?required",
        r"required:?\s*j\.?d\.?\b",
        r"juris\s+doctor(?:ate)?\s+(?:degree\s+)?(?:is\s+)?required",
        r"must\s+(?:have|hold|possess)\s+(?:a\s+|an\s+)?j\.?d\.?\b",
        r"must\s+(?:have|hold|possess)\s+(?:a\s+|an\s+)?juris\s+doctor(?:ate)?",
        r"must\s+(?:have|hold|possess)\s+(?:a\s+)?law\s+degree",
        r"law\s+degree\s+(?:is\s+)?required",
    ]
]

BAR_ADMISSION_REQUIRED_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(?:active\s+|current\s+)?bar\s+admission\s+(?:is\s+)?required",
        r"admission\s+to\s+(?:the\s+)?bar\s+(?:is\s+)?required",
        r"must\s+be\s+admitted\s+to\s+(?:the\s+)?bar",
        r"must\s+be\s+a\s+member\s+of\s+(?:the\s+)?bar",
        r"bar\s+membership\s+(?:is\s+)?required",
        r"licensed\s+attorney\s+required",
        r"must\s+be\s+a\s+licensed\s+attorney",
        r"(?:active\s+)?law\s+license\s+(?:is\s+)?required",
        r"must\s+be\s+admitted\s+to\s+practice\s+law",
    ]
]

ALL_PATTERNS = JD_REQUIRED_PATTERNS + BAR_ADMISSION_REQUIRED_PATTERNS


@dataclass
class JDRequirement:
    excluded: bool
    matched_phrase: str | None = None


def _is_negated(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - _NEGATION_WINDOW) : match_start]
    return bool(_NEGATION_RE.search(window))


def check_jd_requirement(description: str) -> JDRequirement:
    """Check description text for explicit JD/bar-admission-required framing."""
    description = description or ""
    for pattern in ALL_PATTERNS:
        for match in pattern.finditer(description):
            if _is_negated(description, match.start()):
                continue
            return JDRequirement(excluded=True, matched_phrase=match.group(0).strip())
    return JDRequirement(excluded=False)
