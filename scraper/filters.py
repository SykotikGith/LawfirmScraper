"""Keyword-based include/exclude filtering for scraped job postings."""
from __future__ import annotations

import re

INCLUDE_KEYWORDS = [
    "IT",
    "Information Technology",
    "Knowledge Management",
    "KM",
    "AI Enablement",
    "Legal AI",
    "Application Support",
    "IAM",
    "Identity and Access Management",
    "Process Improvement",
    "Innovation",
]

EXCLUDE_KEYWORDS = [
    "attorney",
    "associate",
    "paralegal",
    "legal secretary",
    "network engineer",
    "on-call",
    "on call",
    "24/7",
    "healthcare provider",
    "clinical",
]

# Short/ambiguous tokens (like "IT" or "KM") need word-boundary matching so
# they don't match substrings inside unrelated words (e.g. "IT" in "Litigation").
_SHORT_TOKENS = {"IT", "KM", "IAM", "AI"}


def _pattern_for(keyword: str) -> re.Pattern:
    if keyword.upper() in _SHORT_TOKENS and keyword == keyword.upper():
        return re.compile(rf"\b{re.escape(keyword)}\b")
    return re.compile(re.escape(keyword), re.IGNORECASE)


_INCLUDE_PATTERNS = [(kw, _pattern_for(kw)) for kw in INCLUDE_KEYWORDS]
_EXCLUDE_PATTERNS = [(kw, _pattern_for(kw)) for kw in EXCLUDE_KEYWORDS]

# "Manager" is excluded unless paired with "IT" as a judgment-call IC-adjacent
# title (e.g. "IT Manager"), per the exclusion rule's carve-out.
_MANAGER_RE = re.compile(r"\bmanager\b", re.IGNORECASE)
_IT_MANAGER_RE = re.compile(r"\bIT\s+Manager\b", re.IGNORECASE)


def matches_include(title: str) -> list[str]:
    """Return the include keywords found in the title."""
    return [kw for kw, pat in _INCLUDE_PATTERNS if pat.search(title)]


def matches_exclude(title: str) -> list[str]:
    """Return the exclude keywords found in the title."""
    hits = [kw for kw, pat in _EXCLUDE_PATTERNS if pat.search(title)]
    if _MANAGER_RE.search(title) and not _IT_MANAGER_RE.search(title):
        hits.append("manager (non-IT)")
    return hits


def is_relevant(title: str) -> tuple[bool, list[str], list[str]]:
    """Decide whether a posting title is relevant.

    Returns (keep, include_hits, exclude_hits).
    """
    include_hits = matches_include(title)
    exclude_hits = matches_exclude(title)
    keep = bool(include_hits) and not exclude_hits
    return keep, include_hits, exclude_hits
