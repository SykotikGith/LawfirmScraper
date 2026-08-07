"""CLI entrypoint: scrape all configured firms, filter, dedupe, report."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS
from .config import FIRMS, MANUAL_CHECK_FIRMS
from .filters import Classification, classify
from .jd_requirement import check_jd_requirement
from .models import Posting
from .report import ManualCheckEntry, ReportEntry, write_report
from .store import SeenStore
from .work_arrangement import WorkArrangement, detect_work_arrangement

DEBUG_TITLES_PATH = Path(__file__).resolve().parent.parent / "debug_all_titles.txt"
DESCRIPTION_FETCH_TIMEOUT = 20

# One JSON line per posting shown on the dashboard, every run -- the
# "prediction" half of the eval layer (see eval_verdicts.jsonl, built
# separately from what the user pastes back in). Append-only and never
# overwritten, unlike debug_all_titles.txt, so it accumulates a real history
# across runs instead of only reflecting the most recent one.
EVAL_PREDICTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "eval_predictions.jsonl"


def _is_shared_listing_url(url: str, firm_cfg: dict) -> bool:
    """True when `url` is one of the firm's known list/search/board URLs
    rather than a URL unique to one posting.

    Root-cause fix: some adapters (Venable; viGlobal's postback-only row
    shapes -- O'Melveny, Bryan Cave, Mintz Levin, Winston Taylor -- whose
    "Apply" controls are ASP.NET postback LinkButtons, not real hrefs) give
    *every* posting the exact same fallback URL: the shared list/search
    page, not a page specific to that job. Fetching that page's full text
    and searching it for JD-requirement language is not scoped to any one
    posting -- a phrase found anywhere on the shared page (a different
    job's requirements, sitewide boilerplate, a disclaimer) gets
    misattributed to every single posting checked against it. Confirmed
    live: Mintz Levin's "Knowledge Management and Innovation Strategist"
    was excluded for "J.D. required" that doesn't appear anywhere in that
    job's actual description -- because the fetch hit the shared listing
    page, not a page about that job.

    Skipping the fetch entirely for these URLs (rather than trying to
    scope the search some other way) is the safe fix: no description text
    means the JD check fails open, same as every other missing-data case.
    """
    shared_urls = {
        firm_cfg[key]
        for key in ("list_url", "search_url", "board_url", "api_url")
        if firm_cfg.get(key)
    }
    return url in shared_urls


def _fetch_description(url: str, session: requests.Session, cache: dict[str, str]) -> str:
    """Best-effort single-posting-page text fetch for the JD-requirement check.

    Only called for postings that already passed the title-level and
    work-arrangement filters -- a small enough set that one extra request
    per posting is affordable, unlike fetching a description for every
    posting scraped. Callers must first confirm `url` is NOT a shared
    listing URL (see `_is_shared_listing_url`) -- this function has no way
    to tell a real per-job page from a shared one on its own, and fetching
    a shared page here would reintroduce the misattribution bug described
    above.

    Returns "" on any failure (timeout, non-200, JS-rendered page with no
    server-side text) -- the JD check fails open on empty text, same as
    every other best-effort filter in this project.
    """
    if not url or url == "#":
        return ""
    if url in cache:
        return cache[url]
    try:
        resp = session.get(url, timeout=DESCRIPTION_FETCH_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(separator=" ", strip=True)
    except Exception:  # noqa: BLE001 - best-effort; a failed fetch just means the check can't fire
        text = ""
    cache[url] = text
    return text


def _review_reason_text(tier2_hits: list[str]) -> str:
    return "/".join(h.lower() for h in tier2_hits) + " match"


def _append_prediction(
    eval_file,
    firm_name: str,
    posting: Posting,
    cls: Classification,
    wa: WorkArrangement,
    review_reason: str | None,
    run_timestamp: str,
) -> None:
    """Log one line to eval_predictions.jsonl for a posting the dashboard is
    about to show -- the "what did the scraper decide, and why" record that
    a verdict (from eval_verdicts.jsonl) gets compared against later."""
    record = {
        "posting_url": posting.url,
        "firm": firm_name,
        "title": posting.title,
        "tier": cls.tier,
        "matched_keywords": cls.matched_keywords,
        "review_reason": review_reason,
        "work_arrangement": wa.status,
        "run_timestamp": run_timestamp,
    }
    eval_file.write(json.dumps(record) + "\n")


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
        print(f"         matched: {', '.join(cls.matched_keywords)}")
        if cls.tier == "review":
            print(f"         ⚠ review — Tier 2 match, needs a look ({', '.join(cls.matched_keywords)})")
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

    # One timestamp for the whole run, so every prediction logged during it
    # (across every firm) shares the same run_timestamp -- makes it easy to
    # later ask "what did the classifier look like as of this specific run"
    # rather than getting a slightly different time per posting.
    run_timestamp = datetime.now(timezone.utc).isoformat()
    EVAL_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    eval_predictions_file = EVAL_PREDICTIONS_PATH.open("a", encoding="utf-8")

    jd_check_session = requests.Session()
    jd_check_session.headers.update(DEFAULT_HEADERS)
    description_cache: dict[str, str] = {}

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

            # Only fetch a description for postings that already survived the
            # title-level and work-arrangement filters -- a much smaller set
            # than everything scraped, so one extra request per posting here
            # is affordable in a way it wouldn't be earlier in the pipeline.
            # Never fetch a shared list/search page (see
            # _is_shared_listing_url) -- its text isn't scoped to this
            # posting, so a match found there can't be trusted as being
            # about this job. For postings where fetching isn't possible at
            # all (no genuine per-job URL, e.g. postback-only viGlobal
            # tenants), work-arrangement detection is stuck with whatever
            # the adapter provided at scrape time -- a real, documented
            # coverage gap (same category as work_arrangement.py's existing
            # "most adapters don't have description text" gap), not
            # something this fetch can paper over.
            description = posting.description
            if not description and not _is_shared_listing_url(posting.url, firm_cfg):
                description = _fetch_description(posting.url, jd_check_session, description_cache)
                if description:
                    # Re-check now that a real description might be
                    # available -- catches hybrid/onsite language (e.g. a
                    # percentage-based in-office split) that only shows up
                    # in the full posting text, not the location field the
                    # first pass above was limited to.
                    wa = detect_work_arrangement(posting.location, description)
                    if wa.status in ("onsite", "hybrid"):
                        debug_file.write(
                            f"    -> excluded from {cls.tier}: work arrangement is "
                            f"{wa.status} (found after fetching full description) "
                            f"({'; '.join(wa.signals)})\n"
                        )
                        continue

            jd = check_jd_requirement(description)
            if jd.excluded:
                debug_file.write(
                    f'    -> excluded from {cls.tier}: JD/bar admission required '
                    f'("{jd.matched_phrase}")\n'
                )
                # Also printed to console (not just the debug_all_titles.txt
                # artifact) since the artifact requires downloading a zip from
                # the Actions run to inspect -- this way the exclusion is
                # visible directly in the job's own output/summary too, for
                # tuning without an extra download step.
                print(
                    f'   ⚠ excluding "{posting.title}" ({firm_name}) — JD/bar admission '
                    f'required: "{jd.matched_phrase}"'
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
                _append_prediction(
                    eval_predictions_file, firm_name, posting, cls, wa, None, run_timestamp
                )
                auto_matches.append((posting, cls, is_new, wa))
                report_auto.append(
                    ReportEntry(
                        firm=firm_name,
                        title=posting.title,
                        location=posting.location,
                        url=posting.url,
                        matched_keywords=cls.matched_keywords,
                        is_new=is_new,
                        work_arrangement=work_arrangement_tag,
                    )
                )
            else:
                review_reason = _review_reason_text(cls.matched_keywords)
                _append_prediction(
                    eval_predictions_file, firm_name, posting, cls, wa, review_reason, run_timestamp
                )
                review_matches.append((posting, cls, is_new, wa))
                report_review.append(
                    ReportEntry(
                        firm=firm_name,
                        title=posting.title,
                        location=posting.location,
                        url=posting.url,
                        matched_keywords=cls.matched_keywords,
                        is_new=is_new,
                        review_reason=review_reason,
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
    eval_predictions_file.close()
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
