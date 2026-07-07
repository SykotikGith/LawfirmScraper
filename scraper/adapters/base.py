"""Adapter base class: one adapter type per ATS platform."""
from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from ..models import Posting

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
}


class Adapter(ABC):
    """Fetches raw job postings for one firm from its ATS."""

    ats_name: str = "unknown"

    def __init__(self, firm: str, config: dict):
        self.firm = firm
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @abstractmethod
    def fetch(self) -> list[Posting]:
        """Return every current posting for this firm (unfiltered)."""
        raise NotImplementedError
