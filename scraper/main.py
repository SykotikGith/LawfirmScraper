"""CLI entrypoint: scrape all configured firms, filter, dedupe, report."""
from __future__ import annotations

import argparse
import sys

from .config import FIRMS
from .filters import is_relevant
from .models import Posting
from .store import SeenStore


def scrape_firm(firm_name: str, firm_cfg: dict) -> tuple[list[Posting], str | None]:
    adapter_cls = firm_cfg["adapter"]
    adapter = adapter_cls(firm_name, firm_cfg)
    try:
        return adapter.fetch(), None
    except Exception as exc:  # noqa: BLE001 - report per-firm failures, don't crash the run
        return [], f"{type(exc).__name__}: {exc}"


def run(reset_seen: bool = False) -> int:
    store = SeenStore()
    if reset_seen:
        store._data = {}

    total_new = 0
    print("=" * 72)
    print("Law firm ATS scrape — IT / KM / Legal-AI role filter")
    print("=" * 72)

    for firm_name, firm_cfg in FIRMS.items():
        postings, error = scrape_firm(firm_name, firm_cfg)
        print(f"\n## {firm_name} ({firm_cfg['adapter'].ats_name})")

        if error:
            print(f"   ! fetch failed: {error}")
            continue
        if not postings:
            print("   (no postings returned — check adapter config)")
            continue

        matches = []
        for posting in postings:
            keep, include_hits, _exclude_hits = is_relevant(posting.title)
            if not keep:
                continue
            is_new = store.is_new(firm_name, posting.posting_id)
            matches.append((posting, include_hits, is_new))
            store.mark_seen(firm_name, posting.posting_id)

        if not matches:
            print(f"   {len(postings)} postings scraped, none matched filters")
            continue

        for posting, include_hits, is_new in matches:
            flag = "NEW" if is_new else "seen"
            total_new += 1 if is_new else 0
            print(f"   [{flag}] {posting.title} — {posting.location}")
            print(f"         matched: {', '.join(include_hits)}")
            print(f"         {posting.url}")

    store.save()
    print("\n" + "=" * 72)
    print(f"Done. {total_new} new posting(s) since last run.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset-seen",
        action="store_true",
        help="Ignore the seen-postings store and report every current match as new",
    )
    args = parser.parse_args()
    return run(reset_seen=args.reset_seen)


if __name__ == "__main__":
    sys.exit(main())
