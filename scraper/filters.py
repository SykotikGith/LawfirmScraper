"""Three-tier keyword classification for scraped job postings.

Tiers, in evaluation order:
  excluded    -- a hard-exclude term is present. Never shown in either
                 bucket, regardless of any Tier 1/Tier 2 phrase match.
  none        -- no Tier 1 or Tier 2 phrase found. Not shown.
  auto_match  -- title contains a Tier 1 phrase. Surfaced prominently --
                 these phrases have reliably meant a genuine match.
  review      -- no Tier 1 phrase, but a Tier 2 phrase is present. Noisier,
                 needs eyeballing rather than auto-trust, but real matches
                 have come from this bucket -- surfaced for manual review
                 rather than dropped.

If a title matches both a Tier 1 and a Tier 2 phrase (e.g. "Innovation
Manager - Applied AI" hits Tier 2's "innovation manager" AND Tier 1's
"applied AI"), Tier 1 wins -- it's checked first and short-circuits.

This replaces an earlier design where tier was determined by an AI/KM
keyword combined with a separate Director/Manager "disqualifier" list.
That model made genuinely good titles invisible for two different
reasons: a title like "Practice Technology Manager" never matched any
AI/KM keyword to begin with (dropped as tier "none", not through hard
exclusion -- it just never hit anything), and a title like "Director of
Artificial Intelligence" was dropped the same way (no AI/KM keyword
match either). Neither was a hard-exclude problem; the keyword list
itself was just too narrow, and "Director" acting as a blanket
downgrade-or-drop modifier was too blunt an instrument for a category as
specific as AI-role titles. The current design uses two independent,
purpose-built phrase lists instead -- which list you're in is what
determines the tier, not a keyword-plus-modifier combination. This also
means terms from the old broader AI/KM list that aren't part of either
tier here anymore (e.g. "IAM", "Application Support", "Process
Improvement", "Legal Tech" as a bare term) no longer match at all --
intentional narrowing, not an oversight.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TIER_1_KEYWORDS = [
    "AI enablement",
    "AI adoption",
    "AI training",
    "AI optimization",
    "AI operations",
    "applied AI",
    "AI solution",
    "AI knowledge",
    "practice technology",
    "practice innovation",
    "practice enablement",
    "legal technology advisor",
    "legal innovation",
    "knowledge management",
    "knowledge engineer",
    "digital adoption",
    "technology adoption",
    "technology enablement",
]

# Noisier than Tier 1 -- real matches have come from here, but they need a
# human look rather than automatic trust. Never auto-hidden.
TIER_2_KEYWORDS = [
    "innovation manager",
    "innovation specialist",
    "director of AI",
    "director of artificial intelligence",
    "legal operations",
    "legal solutions",
    "training specialist",
    "training manager",
]

HARD_EXCLUDE_TERMS = [
    "Aderant",
    "IT Asset",
    "IT Asset Specialist",
    "IT Asset Lead",
    "Development Manager",
    # Hands-on build roles -- near-perfect predictor of NOT this kind of
    # role, even when a Tier 1/2 phrase is also present (see
    # classify()'s docstring on precedence). Plain substrings, so these
    # also catch the -ing/-ure/-s forms (Engineering, Architecture,
    # Developers) without needing separate entries -- which is also why
    # the old narrower "Network Engineer" / "Engineering Manager" entries
    # were removed: both are now subsumed by bare "Engineer".
    "Engineer",
    "Developer",
    "Architect",
    "Scientist",
    # Finance/Billing/Accounting
    "Finance",
    "Financial",
    "Billing",
    "Accounting",
    "Accountant",
    # JD/bar-required or support-staff tracks -- not IC-eligible regardless
    # of a Tier 1/2 phrase also being present in the title. Excludes roles
    # like "Knowledge Management Lawyer" / "Knowledge Management Attorney" /
    # "Knowledge Management Counsel" even though they'd otherwise hit
    # Tier 1's "knowledge management".
    "Attorney",
    "Lawyer",
    "Counsel",
    "Associate",
    "Paralegal",
    "Legal Secretary",
    "Of Counsel",
    "Partner",
]

# Terms that need whole-word matching (case-insensitive) so they never match
# as a partial substring inside an unrelated word.
_WHOLE_WORD_TERMS = {"lawyer", "attorney", "counsel"}


def _pattern_for(keyword: str) -> re.Pattern:
    if keyword.lower() in _WHOLE_WORD_TERMS:
        return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    return re.compile(re.escape(keyword), re.IGNORECASE)


def _hits(title: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _pattern_for(kw).search(title)]


@dataclass
class Classification:
    tier: str  # "auto_match" | "review" | "excluded" | "none"
    matched_keywords: list[str] = field(default_factory=list)
    hard_exclude_hits: list[str] = field(default_factory=list)


def classify(title: str) -> Classification:
    """Classify a posting title into one of the four tiers above."""
    hard_hits = _hits(title, HARD_EXCLUDE_TERMS)
    if hard_hits:
        return Classification(tier="excluded", hard_exclude_hits=hard_hits)

    tier1_hits = _hits(title, TIER_1_KEYWORDS)
    if tier1_hits:
        return Classification(tier="auto_match", matched_keywords=tier1_hits)

    tier2_hits = _hits(title, TIER_2_KEYWORDS)
    if tier2_hits:
        return Classification(tier="review", matched_keywords=tier2_hits)

    return Classification(tier="none")
