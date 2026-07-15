"""Static HTML report generator.

Produces report.html (and an identical index.html, so the bare GitHub
Pages root URL works too) styled with a fixed dark navy / hunter-green /
teal palette, so results are viewable from any device via GitHub Pages
without running anything locally.

All scraped text (titles, locations, firm names, URLs) is untrusted
external data -- everything gets html.escape()'d before interpolation.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPORT_PATH = Path(__file__).resolve().parent.parent / "report.html"
INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"

# Country/region names that show up in real AmLaw-100 global-office location
# text. Deliberately NOT an exhaustive list of every non-US place on Earth --
# see _is_us_location's docstring for why that's fine.
_NON_US_COUNTRY_SIGNALS = (
    "united kingdom", "great britain", "england", "scotland", "wales",
    "northern ireland", "ireland", "germany", "france", "belgium",
    "netherlands", "luxembourg", "switzerland", "spain", "italy", "portugal",
    "austria", "poland", "czech republic", "hungary", "sweden", "denmark",
    "norway", "finland", "canada", "mexico", "brazil", "argentina", "chile",
    "colombia", "peru", "china", "hong kong", "japan", "south korea",
    "singapore", "australia", "new zealand", "india", "united arab emirates",
    "saudi arabia", "qatar", "kuwait", "bahrain", "south africa", "kenya",
    "nigeria", "israel", "turkey", "russia", "philippines", "indonesia",
    "malaysia", "thailand", "vietnam", "taiwan",
)
# Major non-US cities that could plausibly show up without their country
# name attached (e.g. "Newcastle upon Tyne, United Kingdom" already matches
# the country list above, but a tenant might just say "Newcastle" or
# "London"). Deliberately excludes short/common names that collide with
# real US towns (there IS a London, KY and a London, OH) -- the risk of
# under-excluding a handful of rare cases is much smaller than the risk of
# over-excluding real US postings, which is the bug this list exists to fix.
_NON_US_CITY_SIGNALS = (
    "newcastle upon tyne", "toronto", "vancouver", "montreal", "dubai",
    "abu dhabi", "sydney", "melbourne", "tokyo", "beijing", "shanghai",
    "munich", "frankfurt", "berlin", "milan", "madrid", "barcelona",
    "zurich", "geneva", "brussels", "amsterdam", "dublin", "mexico city",
    "sao paulo", "johannesburg", "seoul", "mumbai", "bangalore", "riyadh",
    "doha",
)
_NON_US_ABBREV_RE = re.compile(r"\b(UK|UAE)\b")


def _is_us_location(location: str) -> bool:
    """Best-effort US-location detector, from location text alone.

    Defaults to US (True) unless there's a clear non-US signal (a country
    name, a known non-US city) -- an unrecognized bare city name ("Nashville",
    "Chicago"), a spelled-out state ("New York, New York"), "5 Locations", or
    an unspecified/empty location is NOT evidence of being outside the US, so
    it defaults to included, not excluded. Same "don't default to the
    exclusionary bucket without positive evidence" principle already used in
    work_arrangement.py -- an earlier version of this function required
    positive US evidence (a state code, "United States") to include a
    posting, which silently dropped genuine US postings like Wilson Elser's
    "New York, New York" or Sidley Austin's "5 Locations" from "US Only"
    alongside the Norton Rose Fulbright UK postings it was meant to exclude.
    """
    if not location:
        return True
    # Strip periods first so "Washington, D.C." matches the same as "DC".
    cleaned = location.replace(".", "")
    lowered = cleaned.lower()
    if any(sig in lowered for sig in _NON_US_COUNTRY_SIGNALS):
        return False
    if any(sig in lowered for sig in _NON_US_CITY_SIGNALS):
        return False
    if _NON_US_ABBREV_RE.search(cleaned):
        return False
    return True


def _location_tags(location: str, work_arrangement: str | None) -> str:
    tags = []
    if _is_us_location(location):
        tags.append("us")
    if work_arrangement == "Remote":
        tags.append("remote")
    return " ".join(tags)

_CHECK_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
)
_WARN_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/>'
    '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 '
    '1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>'
)
_SEARCH_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round"><circle cx="11" cy="11" r="7"/>'
    '<path d="m21 21-4.35-4.35"/></svg>'
)
_SPARKLE_ICON = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4" />'
    '<path d="m7 7 2.5 2.5M17 7l-2.5 2.5M7 17l2.5-2.5M17 17l-2.5-2.5" /></svg>'
)


@dataclass
class ReportEntry:
    firm: str
    title: str
    location: str
    url: str
    matched_keywords: list[str]
    is_new: bool
    review_reason: str | None = None  # only meaningful for review-manually entries
    # "Remote" or "remote status unclear — verify" -- onsite/hybrid postings
    # never make it into a ReportEntry at all, they're hard-excluded earlier.
    work_arrangement: str | None = None


@dataclass
class ManualCheckEntry:
    firm: str
    reason: str
    url: str
    # Compressed, table-friendly version of `reason` (~3-6 words, "platform —
    # blocker type"). Always populated by the caller -- see
    # main.py's _derive_short_reason() fallback for entries that don't have
    # one hand-authored in config.py's MANUAL_CHECK_FIRMS.
    short_reason: str = ""


def _pill(text: str, css_class: str) -> str:
    return f'<span class="pill {css_class}">{html.escape(text)}</span>'


def _card(entry: ReportEntry, section: str, show_new_badge: bool = True) -> str:
    keyword_pills = "".join(_pill(k, "kw-pill") for k in entry.matched_keywords)
    wa_pill = ""
    if entry.work_arrangement == "Remote":
        wa_pill = _pill(entry.work_arrangement, "wa-pill-remote")
    elif entry.work_arrangement:
        wa_pill = _pill(entry.work_arrangement, "wa-pill-unclear")
    reason_pill = _pill(entry.review_reason, "reason-pill") if entry.review_reason else ""
    new_badge = (
        '<span class="new-badge">NEW</span>' if entry.is_new and show_new_badge else ""
    )
    location = html.escape(entry.location) if entry.location.strip() else "Location not specified"
    safe_url = html.escape(entry.url, quote=True)
    loc_tags = _location_tags(entry.location, entry.work_arrangement)
    loc_attr = f' data-loc="{loc_tags}"' if loc_tags else ""

    # The card used to be a single <a> covering the whole thing; it's now a
    # <div> wrapping an inner link (job title etc.) plus a sibling row of
    # status buttons -- an <a> can't validly contain <button>s, and clicking
    # a button inside an anchor is a click-handling headache. data-url is
    # the localStorage key (the posting's real URL, stable run to run) that
    # the status-tracking JS uses to keep every copy of this same posting
    # (e.g. it may appear in both "New Since Last Run" and its home section)
    # in sync.
    return f"""
      <div class="job-card {section}" data-url="{safe_url}"{loc_attr}>
        <span class="applied-badge">APPLIED</span>
        {new_badge}
        <a class="job-card-link" href="{safe_url}" target="_blank" rel="noopener noreferrer">
          <div class="job-firm">{html.escape(entry.firm)}</div>
          <div class="job-title">{html.escape(entry.title)}</div>
          <div class="job-location">{location}</div>
          <div class="job-tags">{keyword_pills}{wa_pill}{reason_pill}</div>
        </a>
        <div class="job-actions">
          <button type="button" class="status-btn status-btn-applied" data-status-action="applied">✓ Applied</button>
          <button type="button" class="status-btn status-btn-not-interested" data-status-action="not_interested">Not Interested</button>
        </div>
      </div>"""


def _section(
    title: str,
    icon: str,
    entries: list[ReportEntry],
    section: str,
    subtitle: str | None = None,
) -> str:
    header = f'<h2 class="section-title {section}">{icon}{html.escape(title)}</h2>'
    subtitle_html = (
        f'<p class="section-subtitle">{html.escape(subtitle)}</p>' if subtitle else ""
    )
    if not entries:
        return f"""
    <section class="section">
      {header}
      {subtitle_html}
      <p class="empty-state">no matches this run</p>
    </section>"""
    cards = "".join(_card(e, section) for e in entries)
    return f"""
    <section class="section">
      {header}
      {subtitle_html}
      <div class="job-grid">{cards}
      </div>
    </section>"""


def _new_since_section(
    auto_matches: list[ReportEntry], review_matches: list[ReportEntry]
) -> str:
    header = f'<h2 class="section-title new-since">{_SPARKLE_ICON}New Since Last Run</h2>'
    subtitle = (
        '<p class="section-subtitle">Postings that weren\'t here last run -- the '
        "fastest way to see what changed.</p>"
    )
    new_entries = [(e, "auto") for e in auto_matches if e.is_new] + [
        (e, "review") for e in review_matches if e.is_new
    ]
    if not new_entries:
        return f"""
    <section class="section">
      {header}
      {subtitle}
      <p class="empty-state">nothing new since the last run</p>
    </section>"""
    cards = "".join(_card(e, section, show_new_badge=False) for e, section in new_entries)
    return f"""
    <section class="section">
      {header}
      {subtitle}
      <div class="job-grid">{cards}
      </div>
    </section>"""


def _manual_check_row(entry: ManualCheckEntry) -> str:
    safe_url = html.escape(entry.url, quote=True)
    short_reason = entry.short_reason or entry.reason
    return f"""
        <tr>
          <td class="mc-firm">{html.escape(entry.firm)}</td>
          <td class="mc-reason">{html.escape(short_reason)}</td>
          <td class="mc-link"><a href="{safe_url}" target="_blank" rel="noopener noreferrer">Check firm's site →</a></td>
        </tr>"""


def _manual_check_section(entries: list[ManualCheckEntry]) -> str:
    count = len(entries)
    summary = (
        f'<summary class="section-title manual">{_SEARCH_ICON}'
        f"<span>Manual Firm Check</span>"
        f'<span class="section-count">({count})</span>'
        f'<span class="chevron">▸</span></summary>'
    )
    if not entries:
        body = '<p class="empty-state">nothing needs manual checking right now</p>'
    else:
        rows = "".join(_manual_check_row(e) for e in sorted(entries, key=lambda e: e.firm))
        body = (
            '<p class="section-subtitle">Scraper can\'t reach this firm automatically — '
            "worth checking by hand.</p>"
            '<div class="manual-check-table-wrap"><table class="manual-check-table">'
            "<thead><tr><th>Firm</th><th>Reason</th><th>Link</th></tr></thead>"
            f"<tbody>{rows}\n        </tbody>"
            "</table></div>"
        )
    return f"""
    <details class="section manual-check-details">
      {summary}
      {body}
    </details>"""


def _metric_card(value: str, label: str, css_class: str = "") -> str:
    return f"""
      <div class="metric-card">
        <div class="metric-value {css_class}">{html.escape(value)}</div>
        <div class="metric-label">{html.escape(label)}</div>
      </div>"""


def _metric_card_new_total(new_count: int, total_count: int) -> str:
    return f"""
      <div class="metric-card">
        <div class="metric-value-stack">
          <div class="metric-stack-line"><span class="metric-stack-tag">New:</span> <span class="accent-green">{new_count}</span></div>
          <div class="metric-stack-line"><span class="metric-stack-tag">Total:</span> <span>{total_count}</span></div>
        </div>
        <div class="metric-label">Matches this run</div>
      </div>"""


def _metric_card_coverage(automated_full: int, partial: int, manual: int) -> str:
    tracked = automated_full + partial + manual
    return f"""
      <div class="metric-card">
        <div class="metric-value-stack">
          <div class="metric-stack-line"><span class="metric-stack-tag">Automated:</span> <span class="accent-green">{automated_full}</span></div>
          <div class="metric-stack-line"><span class="metric-stack-tag">Partial:</span> <span class="accent-amber">{partial}</span></div>
          <div class="metric-stack-line"><span class="metric-stack-tag">Manual:</span> <span class="accent-amber">{manual}</span></div>
        </div>
        <div class="metric-label">Firm coverage ({tracked} tracked)</div>
      </div>"""


def render_report(
    auto_matches: list[ReportEntry],
    review_matches: list[ReportEntry],
    firms_scanned: int,
    manual_check: list[ManualCheckEntry] | None = None,
    generated_at: datetime | None = None,
    firms_partial: int = 0,
    firms_manual: int = 0,
) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    manual_check = manual_check or []
    new_count = sum(1 for e in auto_matches + review_matches if e.is_new)
    total_count = len(auto_matches) + len(review_matches)
    review_count = len(review_matches)
    timestamp_str = generated_at.strftime("%b %d, %Y %I:%M %p UTC")
    firms_automated_full = firms_scanned - firms_partial

    metrics = "".join([
        _metric_card_new_total(new_count, total_count),
        _metric_card_coverage(firms_automated_full, firms_partial, firms_manual),
        _metric_card(str(review_count), "Needs review", "accent-teal"),
        _metric_card(timestamp_str, "Last run", "metric-value-small"),
    ])

    new_since_section = _new_since_section(auto_matches, review_matches)
    auto_section = _section("Auto-match", _CHECK_ICON, auto_matches, "auto")
    review_section = _section(
        "Potential Matches",
        _WARN_ICON,
        review_matches,
        "review",
        subtitle="Needs your judgment — the title matched a keyword but isn't a clear "
        "auto-match.",
    )
    manual_check_section = _manual_check_section(manual_check)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Law Firm Career Radar</title>
<style>
  :root {{
    --bg: #0B121C;
    --card-bg: #101823;
    --job-card-bg: #141D2B;
    --text-primary: #E7EAEE;
    --text-secondary: #9AA5B1;
    --green: #4C8C6B;
    --green-badge-bg: #3E6E52;
    --green-badge-text: #0E1712;
    --green-border: #26344A;
    --teal: #3EA8B5;
    --teal-tag-bg: #153138;
    --teal-tag-text: #9FE0E8;
    --teal-border: #1F4A52;
    --amber: #D9A441;
    --amber-border: #4A3A22;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px 16px 64px;
    background: var(--bg);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .page {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{
    font-size: 1.5rem;
    margin: 0 0 4px;
  }}
  .subtitle {{
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin: 0 0 28px;
  }}
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .loc-filter {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 40px;
  }}
  .loc-filter-btn {{
    font-family: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 7px 16px;
    border-radius: 999px;
    border: 1px solid var(--green-border);
    background: var(--card-bg);
    color: var(--text-secondary);
    cursor: pointer;
    transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
  }}
  .loc-filter-btn:hover {{ border-color: var(--green); color: var(--text-primary); }}
  .loc-filter-btn.active {{
    background: var(--green-badge-bg);
    border-color: var(--green);
    color: var(--green-badge-text);
  }}
  body[data-loc-filter="us"] .job-card:not([data-loc~="us"]) {{ display: none; }}
  body[data-loc-filter="remote"] .job-card:not([data-loc~="remote"]) {{ display: none; }}
  .metric-card {{
    background: var(--card-bg);
    border: 1px solid var(--green-border);
    border-radius: 12px;
    padding: 16px 18px;
  }}
  .metric-value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }}
  .metric-value.accent-green {{ color: var(--green); }}
  .metric-value.accent-teal {{ color: var(--teal); }}
  .metric-value.metric-value-small {{ font-size: 1.05rem; }}
  .metric-value-stack {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .metric-stack-line {{
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.3;
  }}
  .metric-stack-line .accent-green {{ color: var(--green); }}
  .metric-stack-line .accent-amber {{ color: var(--amber); }}
  .metric-stack-tag {{
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-right: 4px;
  }}
  .metric-label {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 4px;
  }}
  .section {{ margin-bottom: 40px; }}
  .section-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.15rem;
    margin: 0 0 16px;
  }}
  .section-title.auto {{ color: var(--green); }}
  .section-title.review {{ color: var(--teal); }}
  .section-title.manual {{ color: var(--amber); }}
  .section-title.new-since {{ color: var(--green); }}
  .section-subtitle {{
    color: var(--text-secondary);
    font-size: 0.85rem;
    margin: -8px 0 16px;
  }}
  .manual-check-details {{
    margin-top: 48px;
    padding-top: 24px;
    border-top: 1px solid var(--amber-border);
  }}
  summary.section-title {{
    cursor: pointer;
    user-select: none;
    list-style: none;
  }}
  summary.section-title::-webkit-details-marker {{ display: none; }}
  summary.section-title::marker {{ content: ""; }}
  .section-count {{
    color: var(--text-secondary);
    font-weight: 400;
    font-size: 0.85rem;
  }}
  .chevron {{
    margin-left: auto;
    font-size: 0.8rem;
    transition: transform 0.15s ease;
  }}
  details[open] .chevron {{ transform: rotate(90deg); }}
  .empty-state {{
    color: var(--text-secondary);
    font-style: italic;
    background: var(--card-bg);
    border: 1px dashed var(--green-border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin: 0;
  }}
  .job-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }}
  .job-card {{
    position: relative;
    display: block;
    background: var(--job-card-bg);
    border-radius: 12px;
    padding: 18px;
    transition: transform 0.12s ease, border-color 0.12s ease, opacity 0.12s ease;
  }}
  .job-card.auto {{ border: 1px solid var(--green-border); }}
  .job-card.review {{ border: 1px solid var(--teal-border); }}
  .job-card:hover {{
    transform: translateY(-2px);
  }}
  .job-card.auto:hover {{ border-color: var(--green); }}
  .job-card.review:hover {{ border-color: var(--teal); }}
  .job-card-link {{
    display: block;
    text-decoration: none;
    color: inherit;
  }}
  .job-firm {{
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }}
  .job-title {{
    font-size: 1.02rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
    line-height: 1.35;
  }}
  .job-location {{
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 12px;
  }}
  .job-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .pill {{
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.72rem;
    padding: 3px 8px;
    border-radius: 999px;
    white-space: nowrap;
  }}
  .kw-pill {{
    background: transparent;
    border: 1px solid var(--green-border);
    color: var(--text-secondary);
  }}
  .job-card.review .kw-pill {{ border-color: var(--teal-border); }}
  .reason-pill {{
    background: var(--teal-tag-bg);
    color: var(--teal-tag-text);
    border: 1px solid var(--teal-border);
  }}
  .wa-pill-remote {{
    background: var(--green-badge-bg);
    color: var(--green-badge-text);
    border: 1px solid var(--green-border);
  }}
  .wa-pill-unclear {{
    background: var(--teal-tag-bg);
    color: var(--teal-tag-text);
    border: 1px solid var(--teal-border);
  }}
  .manual-check-table-wrap {{
    overflow: auto;
    border: 1px solid var(--amber-border);
    border-radius: 12px;
  }}
  .manual-check-table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card-bg);
  }}
  .manual-check-table th {{
    text-align: left;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--amber);
    padding: 10px 16px;
    border-bottom: 1px solid var(--amber-border);
  }}
  .manual-check-table td {{
    padding: 10px 16px;
    font-size: 0.85rem;
    border-bottom: 1px solid var(--amber-border);
    vertical-align: top;
  }}
  .manual-check-table tr:last-child td {{ border-bottom: none; }}
  .manual-check-table tr:hover td {{ background: var(--job-card-bg); }}
  .manual-check-table .mc-firm {{
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
  }}
  .manual-check-table .mc-reason {{ color: var(--text-secondary); }}
  .manual-check-table .mc-link a {{
    color: var(--amber);
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }}
  .manual-check-table .mc-link a:hover {{ text-decoration: underline; }}
  .new-badge {{
    position: absolute;
    top: -8px;
    right: 14px;
    background: var(--green-badge-bg);
    color: var(--green-badge-text);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 3px 9px;
    border-radius: 6px;
    transform: rotate(-4deg);
    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  }}
  .applied-badge {{
    display: none;
    position: absolute;
    top: -8px;
    left: 14px;
    background: var(--card-bg);
    color: var(--text-secondary);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 3px 9px;
    border-radius: 6px;
    border: 1px solid var(--green-border);
    transform: rotate(3deg);
  }}
  .job-card[data-status="applied"] {{ opacity: 0.55; }}
  .job-card[data-status="applied"]:hover {{ opacity: 0.85; }}
  .job-card[data-status="applied"] .applied-badge {{ display: inline-block; }}
  .job-card[data-status="applied"] .new-badge {{ display: none; }}
  .job-card[data-status="not-interested"] {{ display: none; }}
  body[data-show-dismissed="true"] .job-card[data-status="not-interested"] {{
    display: block;
    opacity: 0.5;
  }}
  .job-actions {{
    display: flex;
    gap: 8px;
    margin-top: 12px;
    position: relative;
    z-index: 1;
  }}
  .status-btn {{
    font-family: inherit;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 999px;
    border: 1px solid var(--green-border);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: border-color 0.12s ease, color 0.12s ease, background 0.12s ease;
  }}
  .status-btn:hover {{ border-color: var(--green); color: var(--text-primary); }}
  .job-card[data-status="applied"] .status-btn-applied {{
    background: var(--green-badge-bg);
    border-color: var(--green);
    color: var(--green-badge-text);
  }}
  .job-card[data-status="not-interested"] .status-btn-not-interested,
  body[data-show-dismissed="true"] .job-card[data-status="not-interested"] .status-btn-not-interested {{
    background: var(--amber-border);
    border-color: var(--amber);
    color: var(--amber);
  }}
  .show-dismissed-toggle {{
    font-family: inherit;
    font-size: 0.82rem;
    color: var(--text-secondary);
    background: none;
    border: none;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
    margin-bottom: 40px;
  }}
  .show-dismissed-toggle:hover {{ color: var(--text-primary); }}
  footer {{
    margin-top: 48px;
    color: var(--text-secondary);
    font-size: 0.78rem;
    text-align: center;
  }}
</style>
</head>
<body>
  <div class="page">
    <h1>Law Firm Career Radar</h1>
    <p class="subtitle">IT / Knowledge Management / Legal-AI role filter — updated {html.escape(timestamp_str)}</p>

    <div class="metrics-grid">{metrics}
    </div>

    <div class="loc-filter" role="group" aria-label="Filter by location">
      <button type="button" class="loc-filter-btn active" data-loc-filter="all">All Locations</button>
      <button type="button" class="loc-filter-btn" data-loc-filter="us">US Only</button>
      <button type="button" class="loc-filter-btn" data-loc-filter="remote">Remote</button>
    </div>

    <button type="button" id="show-dismissed-toggle" class="show-dismissed-toggle">Show dismissed</button>
{new_since_section}
{auto_section}
{review_section}
{manual_check_section}
    <footer>Generated automatically by the law firm ATS scraper.</footer>
  </div>
  <script>
    (function () {{
      var buttons = document.querySelectorAll(".loc-filter-btn");
      buttons.forEach(function (btn) {{
        btn.addEventListener("click", function () {{
          buttons.forEach(function (b) {{ b.classList.remove("active"); }});
          btn.classList.add("active");
          document.body.setAttribute("data-loc-filter", btn.getAttribute("data-loc-filter"));
        }});
      }});
    }})();

    (function () {{
      // Per-posting Applied/Not Interested status, kept in localStorage
      // (single-device only -- doesn't sync across browsers/computers,
      // that's an accepted limitation) keyed by the posting's real URL,
      // which is stable across dashboard regenerations even though the
      // rest of the HTML is rebuilt from scratch every run.
      var STORAGE_KEY = "lfcr_posting_status";

      function loadStatuses() {{
        try {{
          return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
        }} catch (e) {{
          return {{}};
        }}
      }}

      function saveStatuses(statuses) {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(statuses));
      }}

      function renderAll() {{
        var statuses = loadStatuses();
        document.querySelectorAll(".job-card[data-url]").forEach(function (card) {{
          var status = statuses[card.getAttribute("data-url")];
          if (status === "applied") {{
            card.setAttribute("data-status", "applied");
          }} else if (status === "not_interested") {{
            card.setAttribute("data-status", "not-interested");
          }} else {{
            card.removeAttribute("data-status");
          }}
        }});
      }}

      document.addEventListener("click", function (e) {{
        var btn = e.target.closest(".status-btn");
        if (!btn) return;
        e.preventDefault();
        var card = btn.closest(".job-card");
        var url = card.getAttribute("data-url");
        var action = btn.getAttribute("data-status-action");
        // Every copy of this posting (it can appear in both "New Since
        // Last Run" and its home section) shares the same URL, so setting
        // status once here and re-rendering all cards keeps them in sync.
        var statuses = loadStatuses();
        statuses[url] = statuses[url] === action ? undefined : action;
        if (statuses[url] === undefined) delete statuses[url];
        saveStatuses(statuses);
        renderAll();
      }});

      var dismissToggle = document.getElementById("show-dismissed-toggle");
      if (dismissToggle) {{
        dismissToggle.addEventListener("click", function () {{
          var shown = document.body.getAttribute("data-show-dismissed") === "true";
          document.body.setAttribute("data-show-dismissed", shown ? "false" : "true");
          dismissToggle.textContent = shown ? "Show dismissed" : "Hide dismissed";
        }});
      }}

      renderAll();
    }})();
  </script>
</body>
</html>
"""


def write_report(
    auto_matches: list[ReportEntry],
    review_matches: list[ReportEntry],
    firms_scanned: int,
    manual_check: list[ManualCheckEntry] | None = None,
    firms_partial: int = 0,
    firms_manual: int = 0,
) -> None:
    html_out = render_report(
        auto_matches,
        review_matches,
        firms_scanned,
        manual_check,
        firms_partial=firms_partial,
        firms_manual=firms_manual,
    )
    REPORT_PATH.write_text(html_out, encoding="utf-8")
    INDEX_PATH.write_text(html_out, encoding="utf-8")
