"""CLI entrypoint: scrape all configured firms, filter, dedupe, report."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .config import FIRMS, MANUAL_CHECK_FIRMS
from .filters import Classification, classify
from .models import Posting
from .report import ManualCheckEntry, ReportEntry, write_report
from .store import SeenStore
from .work_arrangement import WorkArrangement, detect_work_arrangement

DEBUG_TITLES_PATH = Path(__file__).resolve().parent.parent / "debug_all_titles.txt"


def _review_reason_text(mgmt_hits: list[str]) -> str:
    return "/".join(h.lower() for h in mgmt_hits) + " title"


def _best_effort_check_url(firm_cfg: dict) -> str:
    for key in ("list_url", "board_url", "search_url", "api_url"):
        if key in firm_cfg:
            return firm_cfg[key]
    if "cxs_host" in firm_cfg and "tenant" in firm_cfg:
        return f"https://{firm_cfg['cxs_host']}/recruiting/{firm_cfg['tenant']}/{firm_cfg.get('site', '')}"
    if "tenant" in firm_cfg and "wd" in firm_cfg:
        return f"https://{firm_cfg['tenant']}.{firm_cfg['wd']}.myworkdayjobs.com/{firm_cfg.get('site', '')}"
    if "board_token" in firm_cfg:
        return f"https://job-boards.greenhouse.io/{firm_cfg['board_token']}"
    return "#"


# Fallback for MANUAL_CHECK_FIRMS entries without a hand-authored
# "short_reason" -- best-effort keyword extraction from the long-form
# `reason` prose, roughly "platform — blocker type". Every current entry
# has a hand-authored short_reason (more accurate than guessing), this only
# protects future entries that forget to add one.
_SHORT_REASON_PLATFORMS = (
    ("iCIMS", "iCIMS"),
    ("Workday", "Workday"),
    ("Coveo", "Coveo"),
    ("RecSolu", "RecSolu"),
    ("Cloudflare", "Cloudflare"),
    ("Imperva", "Imperva"),
    ("ApplicantStack", "ApplicantStack"),
    ("SilkRoad", "SilkRoad"),
    ("Taleo", "Taleo"),
)
_SHORT_REASON_BLOCKERS = (
    ("AWS WAF", "AWS WAF blocked"),
    ("bot-management", "bot-protection blocked"),
    ("bot protection", "bot-protection blocked"),
    ("dormant", "dormant tenant"),
    ("credentials", "requires credentials"),
    ("Unauthorized", "requires auth"),
    ("JS search", "client-side JS only"),
    ("client-side", "client-side JS only"),
    ("email-based apply", "email-apply only"),
    ("no ATS", "no ATS found"),
)


def _derive_short_reason(long_reason: str) -> str:
    lowered = long_reason.lower()
    platform = next(
        (label for kw, label in _SHORT_REASON_PLATFORMS if kw.lower() in lowered), None
    )
    blocker = next(
        (label for kw, label in _SHORT_REASON_BLOCKERS if kw.lower() in lowered), None
    )
    if platform and blocker:
        return f"{platform} — {blocker}"
    if platform:
        return f"{platform} — see notes"
    if blocker:
        return blocker
    return "See notes for detail"


def _dynamic_failure_short_reason(error: str) -> str:
    exc_type = error.split(":", 1)[0]
    if "Timeout" in exc_type:
        return "Network timeout this run"
    if "ConnectionError" in exc_type:
        return "Connection failed this run"
    status_match = re.search(r"\b([45]\d{2})\b", error)
    if status_match:
        return f"HTTP {status_match.group(1)} error this run"
    return "Fetch failed this run"


def scrape_firm(firm_name: str, firm_cfg: dict) -> tuple[list[Posting], str | None]:
    adapter_cls = firm_cfg["adapter"]
    adapter = adapter_cls(firm_name, firm_cfg)
    try:
        return adapter.fetch(), None
    except Exception as exc:  # noqa: BLE001 - report per-firm failures, don't crash the run
        return [], f"{type(exc).__name__}: {exc}"


def _print_bucket(
    label: str, entries: list[tuple[Posting, Classification, bool, WorkArrangement]]
) -> int:
    if not entries:
        return 0
    new_count = 0
    print(f"\n   --- {label} ---")
    for posting, cls, is_new, wa in entries:
        flag = "NEW" if is_new else "seen"
        new_count += 1 if is_new else 0
        print(f"   [{flag}] {posting.title} — {posting.location}")
        print(f"         matched: {', '.join(cls.ai_km_hits)}")
        if cls.tier == "review":
            print(f"         ⚠ review — may be program/people-management-heavy ({', '.join(cls.mgmt_hits)})")
        if wa.status == "unclear":
            print("         ⚠ remote status unclear — verify")
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
    report_auto: list[ReportEntry] = []
    report_review: list[ReportEntry] = []
    dynamic_manual_check: list[ManualCheckEntry] = []

    for firm_name, firm_cfg in FIRMS.items():
        postings, error = scrape_firm(firm_name, firm_cfg)
        print(f"\n## {firm_name} ({firm_cfg['adapter'].ats_name})")

        if error:
            print(f"   ! fetch failed: {error}")
            dynamic_manual_check.append(
                ManualCheckEntry(
                    firm=firm_name,
                    reason=f"adapter fetch failed this run ({error}) — may be transient, "
                    "worth checking by hand if it keeps happening",
                    short_reason=_dynamic_failure_short_reason(error),
                    url=_best_effort_check_url(firm_cfg),
                )
            )
            continue
        if not postings:
            print("   (no postings returned — check adapter config)")
            dynamic_manual_check.append(
                ManualCheckEntry(
                    firm=firm_name,
                    reason="adapter ran but returned zero postings this run — may be "
                    "transient or the site structure changed",
                    short_reason="Zero postings this run",
                    url=_best_effort_check_url(firm_cfg),
                )
            )
            continue

        auto_matches = []
        review_matches = []
        for posting in postings:
            cls = classify(posting.title)
            wa = detect_work_arrangement(posting.location, posting.description)

            debug_line = (
                f"{firm_name} | {posting.title} | {posting.location} | {posting.url} "
                f"| title_tier={cls.tier} | work_arrangement={wa.status}"
            )
            if wa.signals:
                debug_line += f" | signals: {'; '.join(wa.signals)}"
            debug_file.write(debug_line + "\n")

            if cls.tier not in ("auto_match", "review"):
                continue

            if wa.status in ("onsite", "hybrid"):
                debug_file.write(
                    f"    -> excluded from {cls.tier}: work arrangement is {wa.status} "
                    f"({'; '.join(wa.signals)})\n"
                )
                continue

            work_arrangement_tag = None
            if wa.status == "remote":
                work_arrangement_tag = "Remote"
            elif wa.status == "unclear":
                work_arrangement_tag = "remote status unclear — verify"

            is_new = store.is_new(firm_name, posting.posting_id)
            store.mark_seen(firm_name, posting.posting_id)
            if cls.tier == "auto_match":
                auto_matches.append((posting, cls, is_new, wa))
                report_auto.append(
                    ReportEntry(
                        firm=firm_name,
                        title=posting.title,
                        location=posting.location,
                        url=posting.url,
                        matched_keywords=cls.ai_km_hits,
                        is_new=is_new,
                        work_arrangement=work_arrangement_tag,
                    )
                )
            else:
                review_matches.append((posting, cls, is_new, wa))
                report_review.append(
                    ReportEntry(
                        firm=firm_name,
                        title=posting.title,
                        location=posting.location,
                        url=posting.url,
                        matched_keywords=cls.ai_km_hits,
                        is_new=is_new,
                        review_reason=_review_reason_text(cls.mgmt_hits),
                        work_arrangement=work_arrangement_tag,
                    )
                )
        debug_file.flush()

        if not auto_matches and not review_matches:
            print(f"   {len(postings)} postings scraped, none matched filters")
            continue

        total_new += _print_bucket("AUTO-MATCH", auto_matches)
        total_new += _print_bucket("REVIEW MANUALLY", review_matches)

    debug_file.close()
    store.save()

    print("\n" + "=" * 72)
    print(f"MANUAL CHECK NEEDED ({len(MANUAL_CHECK_FIRMS)} firms not automated) — see notes below")
    print("=" * 72)
    static_manual_check: list[ManualCheckEntry] = []
    for firm_name, info in MANUAL_CHECK_FIRMS.items():
        url = info.get("check_url") or info.get("search_url") or info.get("list_url") or "#"
        print(f"\n## {firm_name}")
        if url != "#":
            print(f"   {url}")
        print(f"   {info['reason']}")
        short_reason = info.get("short_reason") or _derive_short_reason(info["reason"])
        static_manual_check.append(
            ManualCheckEntry(
                firm=firm_name, reason=info["reason"], short_reason=short_reason, url=url
            )
        )

    if dynamic_manual_check:
        print("\n" + "=" * 72)
        print(f"ADAPTER FAILURES THIS RUN ({len(dynamic_manual_check)} firms) — see notes below")
        print("=" * 72)
        for entry in dynamic_manual_check:
            print(f"\n## {entry.firm}")
            print(f"   {entry.url}")
            print(f"   {entry.reason}")

    firms_partial = sum(1 for cfg in FIRMS.values() if cfg.get("partial_coverage"))
    write_report(
        report_auto,
        report_review,
        firms_scanned=len(FIRMS),
        manual_check=static_manual_check + dynamic_manual_check,
        firms_partial=firms_partial,
        firms_manual=len(MANUAL_CHECK_FIRMS),
    )

    print("\n" + "=" * 72)
    print(f"Done. {total_new} new posting(s) since last run.")
    print(f"Raw pre-filter titles for every scraped posting written to {DEBUG_TITLES_PATH}")
    print("HTML report written to report.html / index.html")
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
