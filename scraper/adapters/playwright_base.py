"""Playwright (headless Chromium) base adapter.

For firms whose real job data only becomes available after client-side
JS execution -- no discoverable static HTML and no directly-callable
JSON API found via network-request capture -- this launches a real
headless browser and lets the subclass either read the rendered DOM or
intercept a specific network response.

This is deliberately the LAST RESORT fetch path: a full browser launch +
page render is much slower and heavier than a single requests.Session
call, so it's only used for firms confirmed to actually need it (no
clean API discoverable even after inspecting real captured network
traffic) -- every other firm keeps using the existing HTTP-based
adapters. If a firm's real job data turns out to come from a clean JSON
API once discovered via a captured network request, prefer building a
normal HTTP-based adapter against that API directly instead of a
PlaywrightAdapter, even though Playwright was used to *find* it.
"""
from __future__ import annotations

from abc import abstractmethod
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from ..models import Posting
from .base import Adapter, DEFAULT_HEADERS

NAV_TIMEOUT_MS = 30_000


class PlaywrightAdapter(Adapter):
    """Base class for adapters that need a real rendered browser page."""

    @contextmanager
    def _browser_page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])
                page = context.new_page()
                page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
                page.set_default_timeout(NAV_TIMEOUT_MS)
                yield page
            finally:
                browser.close()

    @abstractmethod
    def fetch(self) -> list[Posting]:
        raise NotImplementedError
