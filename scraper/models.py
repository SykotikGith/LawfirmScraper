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
