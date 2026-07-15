"""McDermott Will & Emery adapter -- public Algolia search index.

mcdermottlaw.com/careers/open-roles/ is a WordPress site (wp-search-with-
algolia plugin) that queries a public Algolia index (mws_posts_jobs)
directly from the browser via Algolia's multi-query endpoint
(/1/indexes/*/queries), authenticated with a search-only API key exposed
client-side by design (standard Algolia InstantSearch pattern -- these
keys are meant to be used exactly like this, not a bypass of anything).
Confirmed via live browser network capture: this plain HTTP POST works
standalone, no session/cookies/Playwright needed at all, despite the
mcdermottlaw.com page itself sitting behind an Imperva bot-protection
challenge -- the Algolia index is a separate, ungated origin entirely.

Each hit carries a real numeric post_id, a clean post_title, a relative
permalink, and a free-text job_location field (e.g. "Washington, DC,
Boston, New York") -- everything an adapter needs except a reliable
description: the hit's `content` field is stale/mismatched (confirmed
live -- one hit titled "Senior Design Manager, Events" had `content`
describing an unrelated document-review attorney posting from 2020,
apparently orphaned CMS content never cleaned up), and `post_excerpt` is
identical generic marketing boilerplate on every hit. Neither is used;
description is left empty like most other adapters in this project.

Query scoped server-side to English-locale, business-professionals-
category postings only (job_category_slugs:business-professionals) --
the index's own facet breakdown showed lawyers/law-students categories
mixed in, and McDermott's own taxonomy already reliably separates them,
so there's no reason to pull (and then locally filter out) attorney
postings at all.
"""
from __future__ import annotations

from urllib.parse import urlencode, urljoin

from ..models import Posting
from .base import Adapter

ALGOLIA_URL = "https://8wct17sc6s-dsn.algolia.net/1/indexes/*/queries"
ALGOLIA_QUERY_PARAMS = {
    "x-algolia-agent": "Algolia for JavaScript (4.18.0); Browser (lite)",
    "x-algolia-api-key": "3dab8b7713e0e771d8982186252024b5",
    "x-algolia-application-id": "8WCT17SC6S",
}
SITE_BASE = "https://www.mcdermottlaw.com"


class McDermottAdapter(Adapter):
    ats_name = "Algolia (McDermott)"

    def fetch(self) -> list[Posting]:
        index_name = self.config.get("index_name", "mws_posts_jobs")
        params_str = urlencode(
            {
                "query": "",
                "page": 0,
                "hitsPerPage": 500,
                "filters": "(locale:en OR locale:false) AND "
                "job_category_slugs:business-professionals",
            }
        )
        body = {"requests": [{"indexName": index_name, "params": params_str}]}

        resp = self.session.post(
            ALGOLIA_URL, params=ALGOLIA_QUERY_PARAMS, json=body, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("results", [{}])[0].get("hits", [])

        postings: list[Posting] = []
        for hit in hits:
            title = hit.get("post_title", "")
            posting_id = str(hit.get("post_id", ""))
            if not title or not posting_id:
                continue
            location = hit.get("job_location", "")
            url = urljoin(SITE_BASE, hit.get("permalink", ""))
            postings.append(
                Posting(
                    firm=self.firm,
                    title=title,
                    location=location,
                    url=url,
                    posting_id=posting_id,
                    ats=self.ats_name,
                )
            )
        return postings
