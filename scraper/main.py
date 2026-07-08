"""CLI entrypoint: scrape all configured firms, filter, dedupe, report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import FIRMS
from .filters import Classification, classify
from .models import Posting
from .store import SeenStore

DEBUG_TITLES_PATH = Path(__file__).resolve().parent.parent / "debug_all_titles.txt"


def scrape_firm(firm_name: str, firm_cfg: dict) -> tuple[list[Posting], str | None]:
    adapter_cls = firm_cfg["adapter"]
    adapter = adapter_cls(firm_name, firm_cfg)
    try:
        return adapter.fetch(), None
    except Exception as exc:  # noqa: BLE001 - report per-firm failures, don't crash the run
        return [], f"{type(exc).__name__}: {exc}"


def _print_bucket(label: str, entries: list[tuple[Posting, Classification, bool]]) -> int:
    if not entries:
        return 0
    new_count = 0
    print(f"\n   --- {label} ---")
    for posting, cls, is_new in entries:
        flag = "NEW" if is_new else "seen"
        new_count += 1 if is_new else 0
        print(f"   [{flag}] {posting.title} — {posting.location}")
        print(f"         matched: {', '.join(cls.ai_km_hits)}")
        if cls.tier == "review":
            print(f"         ⚠ review — may be program/people-management-heavy ({', '.join(cls.mgmt_hits)})")
        print(f"         {posting.url}")
    return new_count


def run(reset_seen: bool = False) -> int:
    store = SeenStore()
    if reset_seen:
        store._data = {}

    total_new = 0
    print("=" * 72)
    print("Law firm ATS scrape — IT / KM / Legal-AI role filter")
    print("=" * 72)

    debug_file = DEBUG_TITLES_PATH.open("w", encoding="utf-8")

    for firm_name, firm_cfg in FIRMS.items():
        postings, error = scrape_firm(firm_name, firm_cfg)
        print(f"\n## {firm_name} ({firm_cfg['adapter'].ats_name})")

        if error:
            print(f"   ! fetch failed: {error}")
            continue
        if not postings:
            print("   (no postings returned — check adapter config)")
            continue

        for posting in postings:
            debug_file.write(f"{firm_name} | {posting.title} | {posting.url}\n")
        debug_file.flush()

        auto_matches = []
        review_matches = []
        for posting in postings:
            cls = classify(posting.title)
            if cls.tier not in ("auto_match", "review"):
                continue
            is_new = store.is_new(firm_name, posting.posting_id)
            store.mark_seen(firm_name, posting.posting_id)
            if cls.tier == "auto_match":
                auto_matches.append((posting, cls, is_new))
            else:
                review_matches.append((posting, cls, is_new))

        if not auto_matches and not review_matches:
            print(f"   {len(postings)} postings scraped, none matched filters")
            continue

        total_new += _print_bucket("AUTO-MATCH", auto_matches)
        total_new += _print_bucket("REVIEW MANUALLY", review_matches)

    debug_file.close()
    store.save()
    print("\n" + "=" * 72)
    print(f"Done. {total_new} new posting(s) since last run.")
    print(f"Raw pre-filter titles for every scraped posting written to {DEBUG_TITLES_PATH}")
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
