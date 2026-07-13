"""Three-tier keyword classification for scraped job postings.

Tiers, in evaluation order:
  excluded    -- a hard-exclude term is present. Never shown in either
                 bucket, regardless of any AI/KM keyword match.
  none        -- no AI/KM keyword hit at all. Not shown.
  auto_match  -- an AI/KM keyword hit, and no Director/Manager/Program
                 Manager/Project Manager term present.
  review      -- an AI/KM keyword hit, disqualified from auto_match by a
                 Director/Program Manager/Project Manager term specifically.
                 A title disqualified only by a bare "Manager" that isn't
                 "Program Manager" / "Project Manager" (e.g. "IT Manager")
                 falls through to "none" instead -- it's deliberately not in
                 the review-trigger list, so it's dropped rather than
                 flagged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

AI_KM_KEYWORDS = [
    "Knowledge Management",
    "KM",
    "Legal AI",
    "AI Enablement",
    "AI Practice Transformation",
    "Legal Technology",
    "Legal Tech",
    "IAM",
    "Identity and Access Management",
    "Application Support",
    "Process Improvement",
    "Business Process Optimization",
]

# Disqualifies a title from the auto-match tier.
AUTO_EXCLUDE_MGMT_TERMS = ["Director", "Manager", "Program Manager", "Project Manager"]

# Subset of AUTO_EXCLUDE_MGMT_TERMS that routes a disqualified title into the
# review-manually bucket instead of dropping it silently.
REVIEW_MGMT_TERMS = ["Director", "Program Manager", "Project Manager"]

HARD_EXCLUDE_TERMS = [
    "Aderant",
    "IT Asset",
    "IT Asset Specialist",
    "IT Asset Lead",
    "Network Engineer",
    "Engineering Manager",
    "Development Manager",
    # Finance/Billing/Accounting
    "Finance",
    "Financial",
    "Billing",
    "Accounting",
    "Accountant",
    # JD/bar-required or support-staff tracks -- not IC-eligible regardless
    # of an AI/KM keyword also being present in the title. Excludes roles
    # like "Knowledge Management Lawyer" / "Knowledge Management Attorney" /
    # "Knowledge Management Counsel" even though they'd otherwise hit an
    # AI/KM keyword above.
    "Attorney",
    "Lawyer",
    "Counsel",
    "Associate",
    "Paralegal",
    "Legal Secretary",
    "Of Counsel",
    "Partner",
]

# Short/ambiguous tokens need case-sensitive, word-boundary matching so they
# don't match substrings inside unrelated words or lowercase false positives.
_SHORT_TOKENS = {"KM", "IAM"}

# Terms that need whole-word matching (case-insensitive) so they never match
# as a partial substring inside an unrelated word.
_WHOLE_WORD_TERMS = {"lawyer", "attorney", "counsel"}


def _pattern_for(keyword: str) -> re.Pattern:
    if keyword.upper() in _SHORT_TOKENS and keyword == keyword.upper():
        return re.compile(rf"\b{re.escape(keyword)}\b")
    if keyword.lower() in _WHOLE_WORD_TERMS:
        return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    return re.compile(re.escape(keyword), re.IGNORECASE)


def _hits(title: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _pattern_for(kw).search(title)]


@dataclass
class Classification:
    tier: str  # "auto_match" | "review" | "excluded" | "none"
    ai_km_hits: list[str] = field(default_factory=list)
    mgmt_hits: list[str] = field(default_factory=list)
    hard_exclude_hits: list[str] = field(default_factory=list)


def classify(title: str) -> Classification:
    """Classify a posting title into one of the four tiers above."""
    hard_hits = _hits(title, HARD_EXCLUDE_TERMS)
    if hard_hits:
        return Classification(tier="excluded", hard_exclude_hits=hard_hits)

    ai_km_hits = _hits(title, AI_KM_KEYWORDS)
    if not ai_km_hits:
        return Classification(tier="none")

    auto_disqualifiers = _hits(title, AUTO_EXCLUDE_MGMT_TERMS)
    if not auto_disqualifiers:
        return Classification(tier="auto_match", ai_km_hits=ai_km_hits)

    review_triggers = _hits(title, REVIEW_MGMT_TERMS)
    if review_triggers:
        return Classification(tier="review", ai_km_hits=ai_km_hits, mgmt_hits=review_triggers)

    return Classification(tier="none")
