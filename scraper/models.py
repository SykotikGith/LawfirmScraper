"""Shared data types for the scraper."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Posting:
    firm: str
    title: str
    location: str
    url: str
    posting_id: str
    ats: str
    # Full job description text, when the adapter already has it on hand from
    # data it fetched anyway (no extra per-job HTTP request). Empty string
    # when unavailable -- detection code must tolerate that and fall back to
    # location-only signals.
    description: str = ""
