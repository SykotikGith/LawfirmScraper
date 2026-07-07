"""Persistent seen-postings store, used to dedupe scraper runs over time."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_postings.json"


class SeenStore:
    """Tracks job posting IDs already reported, per firm."""

    def __init__(self, path: Path = DEFAULT_STORE_PATH):
        self.path = path
        self._data: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

    def is_new(self, firm: str, posting_id: str) -> bool:
        return posting_id not in self._data.get(firm, [])

    def mark_seen(self, firm: str, posting_id: str) -> None:
        self._data.setdefault(firm, [])
        if posting_id not in self._data[firm]:
            self._data[firm].append(posting_id)
