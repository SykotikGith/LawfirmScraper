# Law Firm Career Radar

Scrapes career sites at law firms for open business-professional roles in
IT, Knowledge Management, Legal AI, and related areas, classifies each
posting into auto-match / needs-review / excluded, tracks what's already
been seen, and publishes a static HTML report. Runs on a schedule via
GitHub Actions.

(Repo formerly named `LawFirmScraper` — renamed to `law-firm-career-radar`
to better reflect what the project actually does. See `squirrel_notes.md`
for the rename history.)

## Usage

```bash
pip install -r requirements.txt
python -m scraper.main          # scrape + report, remembering what's been seen
python -m scraper.main --reset-seen   # report every current match as "new"
```

Each run prints a per-firm breakdown to the console, then a "MANUAL CHECK
NEEDED" section listing firms that can't be automated (see below), and
finally writes:

- `data/seen_postings.json` — dedup store of posting IDs already reported,
  so subsequent runs only flag genuinely new postings.
- `debug_all_titles.txt` — one line per scraped posting (`Firm | Title |
  Location | URL | title_tier=... | work_arrangement=...`, plus a
  `signals:` note when the work-arrangement detector found any), matched
  or not, for tuning the title and work-arrangement filters against real
  data. Postings hard-excluded for being onsite/hybrid, or for explicit
  JD/bar-admission-required language (see the JD-requirement filter
  below), get an extra `-> excluded from ...` line explaining why —
  including the exact matched phrase for a JD/bar-admission exclusion.
- `report.html` / `index.html` — an identical static HTML report (see
  below), regenerated every run.
- `data/eval_predictions.jsonl` — append-only, one JSON line per posting
  shown on the dashboard each run (`posting_url`, `firm`, `title`, `tier`,
  `matched_keywords`, `review_reason`, `work_arrangement`,
  `run_timestamp`). This is the "what did the classifier decide, and why"
  half of the eval layer described below — unlike every other output file,
  it's never overwritten, so it accumulates real history across runs
  instead of only reflecting the most recent one.

The live report is published via GitHub Pages at
https://sykotikgith.github.io/law-firm-career-radar/.

## Filters

`scraper/filters.py` sorts every scraped title into one of four tiers, in
this order:

1. **Excluded** — a hard-exclude term is present (`HARD_EXCLUDE_TERMS`):
   Aderant, IT Asset (+ Specialist/Lead), Network Engineer, Engineering
   Manager, Development Manager, Finance/Financial/Billing/Accounting/
   Accountant, and JD/bar-required or support-staff titles (Attorney,
   Lawyer, Counsel, Associate, Paralegal, Legal Secretary, Of Counsel,
   Partner).
   Checked first — wins over an AI/KM keyword match every time, so e.g.
   "Knowledge Management Attorney" is excluded.
2. **Auto-match** — the title contains an AI/KM keyword
   (`AI_KM_KEYWORDS`: Knowledge Management, KM, Legal AI, AI Enablement,
   AI Practice Transformation, Legal Technology, Legal Tech, IAM, Identity
   and Access Management, Application Support, Process Improvement,
   Business Process Optimization) and none of Director/Manager/Program
   Manager/Project Manager.
3. **Review manually** — same AI/KM keyword hit, but disqualified from
   auto-match specifically by Director, Program Manager, or Project
   Manager (a bare "Manager" that isn't one of those, e.g. "IT Manager",
   is dropped instead of flagged — deliberately not in the review-trigger
   list).
4. **None** — no AI/KM keyword hit at all, or dropped per the bare-Manager
   rule above. Not shown anywhere.

Only the auto-match and review-manually tiers show up in console output
and the HTML report.

### Work-arrangement filter

`scraper/work_arrangement.py` separately classifies every posting that
survives the title filter above as **remote**, **hybrid**, **onsite**, or
**unclear**, from its location text and (where an adapter already has it
on hand — see below) job description text:

- **Remote** — location says "Remote", "Virtual", or "Nationwide", or the
  description explicitly says fully remote / work from home.
- **Hybrid** — location or description says "hybrid", or names a partial
  in-office schedule, either day-count ("3 days a week in office") or
  percentage-based ("60% in-office presence").
- **Onsite** — only when there's *explicit* contradicting language: location
  says "onsite"/"on-site" directly, or description says something like
  "on-site required," "must work from the office," or "not eligible for
  remote." A plain city/office location by itself is deliberately **not**
  treated as an onsite signal — silence about work arrangement means
  "verify," not "confirmed onsite" (most postings don't state it either
  way, and defaulting a bare "Chicago, IL" to onsite was excluding
  postings that were actually hybrid or remote-eligible but just didn't
  say so in the location field).
- **Unclear** — none of the above signals found. This is the default for a
  plain city/office location with no explicit language either way.

Hybrid and onsite postings are hard-excluded from auto-match/review-manually
the same way title-level hard excludes are — they're written to
`debug_all_titles.txt` with the exclusion reason, but never shown in
console output or the HTML report. Remote postings flow through tagged
"Remote"; unclear postings flow through tagged "remote status unclear —
verify" so they get a second look rather than being silently trusted.

Full job description text (a stronger signal than location alone) is only
available *at scrape time* for adapters that already fetch it as part of
the data they'd pull anyway, at no extra request cost: Greenhouse
(`content=true` on the existing API call), Oracle Recruiting Cloud
(`WorkplaceType`/`WorkplaceTypeCode` plus description fields), and
viGlobal (trailing text already present in the row it scrapes). Every
other adapter — Workday, Circa Works, ApplicantStack, and custom-HTML
firms — detects work arrangement from location text alone at this stage,
since fetching a full description for every scraped posting (hundreds
across 70 firms) would mean an extra HTTP request per posting; those
firms lean on "onsite"/"unclear" more often here as a result. Once a
posting survives that first pass, `main.py` re-checks work arrangement a
second time against whatever description the JD-requirement filter below
fetches (reusing the same fetch, no extra request) — this is what catches
hybrid/onsite language that only appears in the full posting text, not
the location field alone. That re-check is skipped, same as the JD
check itself, for postings with no genuine per-job URL to safely fetch
(see below) — a real, known coverage gap for those specific ATS shapes,
not a bug.

### JD-requirement filter

`scraper/jd_requirement.py` runs after the title and work-arrangement
filters, on the much smaller set of postings that already survived both
(typically a couple dozen per run, not the hundreds scraped) — small
enough that fetching each one's full description page on demand (one
extra HTTP request per posting, cached per-run by URL) is affordable in
a way it isn't earlier in the pipeline. If the adapter already has a
description on hand (Greenhouse/Oracle/viGlobal, see above), that's
reused instead of a redundant fetch.

The fetch is only attempted when `posting.url` is a genuine per-job
URL — `main.py`'s `_is_shared_listing_url()` skips it when the URL is
actually the firm's shared list/search page (`list_url`/`search_url`/
`board_url`/`api_url` in `config.py`), which is what some adapters fall
back to when there's no real per-job link at all (Venable; viGlobal's
postback-only row shapes — O'Melveny, Bryan Cave, Mintz Levin, Winston
Taylor — whose "Apply" controls are ASP.NET postback LinkButtons, not
real hrefs). Fetching a shared page and searching its whole text isn't
scoped to any one posting — CONFIRMED live: Mintz Levin's "Knowledge
Management and Innovation Strategist" was once excluded for "J.D.
required" that doesn't appear anywhere in that job's actual description,
because the fetch hit the shared listing page (every Mintz Levin posting
falls back to the same URL) and matched text belonging to something else
entirely on that page. Skipping the fetch for shared URLs closes this at
the root; it also means work-arrangement and JD-requirement detection
for postings on these specific ATS shapes stays limited to whatever the
adapter provides at scrape time (location text only, for viGlobal's
structured row shape) — a real, known coverage gap, not a bug, same
category as the description-availability gap other adapters already
have.

Looks for EXPLICIT "required" framing around a law degree or bar
admission — "J.D. required," "must have a J.D.," "active bar admission
required," "licensed attorney required," etc. — and hard-excludes the
posting if found, the same way title-level hard excludes work. Every
pattern requires "required" (or must have/hold/possess) wording
specifically, so "preferred"/"a plus"/"nice to have" framing around a JD
never matches to begin with — no separate suppression logic needed.
Negation-aware ("no J.D. required," "law degree not required" don't
trigger it). Fails open on missing/unfetchable description text (network
failure, JS-rendered detail page with no server-side text) — the
posting stays visible rather than being wrongly excluded, the same
"don't default to the exclusionary bucket without positive evidence"
principle used throughout this project's filters. Every exclusion is
logged both to `debug_all_titles.txt` (with the exact matched phrase)
and printed to console, so it shows up in the GitHub Actions run's Step
Summary directly, without needing to download the debug artifact — this
can be tuned the same way the title-level Lawyer/Attorney/Counsel
exclusions were.

## Firm coverage

`scraper/config.py` has three top-level structures:

- `FIRMS` — the active, automated firm list (adapter class + tenant/URL
  config per firm). This is what `main.py` actually scrapes. Currently 70
  firms, 2 of which carry a `partial_coverage` note (Akin Gump, Kirkland &
  Ellis — both confirmed page-1-only due to pagination the adapter can't
  get past) — surfaced on the dashboard as a distinct "Partial" count in
  the "Firm coverage" metric card, alongside "Automated" (the rest of
  `FIRMS`) and "Manual" (`len(MANUAL_CHECK_FIRMS)`), summing to a
  "tracked" total.
- `MANUAL_CHECK_FIRMS` — confirmed real target firms that can't be
  reliably automated (blocked by bot protection, no ATS trace in static
  HTML anywhere discoverable via sitemap search, a real ATS exists but
  requires authentication, or a real ATS exists but has no relevant
  listings). Not scraped; printed as a reminder list at the end of every
  run instead, with a check URL and the reason. Currently 17 firms,
  split into two tiers: confirmed genuine technical obstacles
  (WAF/bot-protection, credential-gated API, or a JS-rendered page with a
  confirmed real ATS/tenant underneath, including several Cloudflare/AWS
  WAF blocks confirmed with a genuine headless-browser session, not just
  plain HTTP) versus unresearched leads (no confirmed block, no
  confirmed absence of postings either) still awaiting a fresh look.
- `REJECTED_LEADS` — slug guesses that turned out to be a different,
  unrelated company on a shared ATS platform (confirmed via real sample
  titles), kept on record so they aren't accidentally retried. Currently 2
  entries.

Adapters live in `scraper/adapters/` — one per ATS platform: iCIMS,
Workday (25 firms), Oracle Recruiting Cloud (2 firms), ApplicantStack, Greenhouse (3
firms), Circa Works, viGlobal (8 firms), UKG/UltiPro Recruiting (6 firms),
PageUp/eArcu, Jobvite, Breezy HR, Radancy, AEM Career Search, FloRecruit,
Dentons Career Search, a generic custom-HTML adapter (12 firms), and
three Playwright-backed adapters (Venable, Paul Weiss, Kirkland & Ellis)
for firms whose job data has no plain-HTTP-reachable form at all, plus
one more (McDermott) that turned out to have a plain public JSON API
once found via Playwright network capture, so it doesn't need a browser
at scrape time despite the site itself sitting behind bot protection.
Kirkland & Ellis is page-1-only (confirmed hard pagination block, ~25 of
~155 postings) — see `config.py`'s notes for that entry. (The iCIMS
adapter exists but currently has no active `FIRMS` entries — every iCIMS
tenant found so far sits behind an AWS WAF challenge, confirmed to still
block a genuine headless-browser session too, and lives in
`MANUAL_CHECK_FIRMS` instead.)

Several career sites sit behind bot protection that blocks plain HTTP
scraping, or turned out to run entirely client-side with no static HTML
trace of the real ATS — those are documented per-firm in `config.py` and
in `MANUAL_CHECK_FIRMS`, rather than left as adapters that fail every run.

### Research/verification scripts

These aren't part of the regular scrape — they were used to discover and
verify the endpoints now baked into `config.py`, and are kept around for
extending coverage to new firms:

- `scraper/ats_probe.py` — bulk-detects which ATS platform a batch of
  firms uses, by slug guessing against known URL patterns.
- `scraper/verify_batch.py` / `scraper/find_workday_sites.py` — live-fetch
  verification for firms `ats_probe.py` flagged, including Workday
  site-slug discovery.
- `scraper/diagnose.py` — scratch space for one-off investigation of a
  specific firm's page/API structure. Gets overwritten repeatedly; not
  meant to hold long-term logic.

## HTML report

`scraper/report.py` renders `report.html` (and an identical `index.html`)
on every run: a metrics row (new matches, firm coverage, needs review,
last run time), an "All Locations / US Only / Remote" filter toolbar
(client-side, no server round-trip — a small vanilla-JS click handler
toggles a `data-loc-filter` attribute on `<body>`, and CSS `:not([data-loc~=...])`
rules hide non-matching cards; each card's US/Remote tags are computed at
render time in `_location_tags()`/`_is_us_location()` from its location text
and work-arrangement status — defaults to US unless there's a clear non-US
signal (a country name, a known non-US city like Norton Rose Fulbright's
Newcastle, UK listings), so an unrecognized bare city name, a spelled-out
state, "5 Locations," or an unspecified location doesn't get silently
excluded from "US Only" the way an earlier positive-match version did), a
"New Since Last Run" section at the top (a filtered
view — every posting flagged new, pulled from both the auto-match and
review pools, so "what changed" doesn't require scanning the full list;
these same postings still appear in their normal section below too, NEW
badge and all), an auto-match section, and a "Potential Matches" section
(the review-manually tier — titled "Needs your judgment" on the
dashboard, since it's about the job title itself needing a second look,
not a scraper problem), each posting card linking straight to the real
job listing. Each card shows keyword-match pills, a work-arrangement pill
("Remote" or "remote status unclear — verify" — see the work-arrangement
filter above) in the same monospace pill style, and a rotated "NEW" badge
for postings not seen on a previous run (suppressed in the "New Since
Last Run" section itself, where it'd be redundant). Empty sections show a
plain "no matches this run" (or "nothing new since the last run") message.
All scraped text is treated as untrusted and HTML-escaped before
rendering.

Every Auto-match/Potential-Matches card also has "✓ Applied" / "Not
Interested" buttons, tracked client-side in `localStorage` keyed by the
posting's own URL (stable across dashboard regenerations even though the
rest of the HTML is rebuilt from scratch every run) — single-device only,
an accepted limitation since `localStorage` doesn't sync across browsers.
Applied dims the card, adds an "APPLIED" badge, and suppresses its NEW
badge (even if the same posting somehow gets re-flagged new in a future
run, it won't look urgent again); Not Interested hides the card
everywhere it appears (including in "New Since Last Run", since the same
`data-url` drives every copy) until the "Show dismissed" toggle near the
top reveals it again, e.g. to undo a mis-click (clicking the same status
button again clears it). Each button's HTML structure changed from a
single `<a class="job-card">` to a `<div class="job-card">` wrapping an
inner `<a class="job-card-link">` plus the status buttons as siblings —
an anchor can't validly contain `<button>`s.

A third section, "Manual Firm Check" (amber accent, collapsed by default
in a `<details>` toggle below a divider so it doesn't dominate the page),
lists every firm the scraper couldn't reach automatically — combining
`MANUAL_CHECK_FIRMS` (the permanent, documented list: WAF blocks,
SPA-only sites, no discoverable ATS, etc.) with any active `FIRMS` entry
whose adapter failed or returned zero postings *this specific run*
(which might be transient, or might be the first sign a site changed
structure). Rendered as a compact Firm / Reason / Link table (not cards
— with ~20 entries, cards took far more vertical space than the content
justified) linking straight to the firm's careers page or main site to
check by hand. The Reason column is a compressed ~3-6-word version
("iCIMS — AWS WAF blocked", "Workday (dormant), no careers page found")
of the full diagnostic paragraph still tracked in `config.py` — each
`MANUAL_CHECK_FIRMS` entry carries an explicit hand-authored
`short_reason` key (more accurate than an automated guess, and there
are only ~17 of them); `main.py`'s `_derive_short_reason()` is a
keyword-extraction fallback for any entry that doesn't (mainly a safety
net for future entries), and `_dynamic_failure_short_reason()` covers
this-run-only adapter failures (timeouts, HTTP error codes, zero
postings) that can't be hand-authored ahead of time. Named and
separated from "Potential Matches" specifically because the two are
easy to conflate but mean different things: one is about a job
title needing a judgment call, the other is about the scraper's
technical reach.

## Eval layer

A small system for measuring how accurate the title/keyword classifier
actually is, separate from running the scraper itself. In progress —
this section covers what's built so far.

`data/eval_predictions.jsonl` (see Usage above) is the "predictions" half:
one line per posting the dashboard shows, every run, recording the tier it
landed in and why. It's intentionally scoped to only what gets *shown* —
there's no way to measure how many genuine matches got wrongly excluded
before ever reaching the dashboard, since those are never seen to be
judged. That's a real, structural blind spot in what this eval layer can
measure (precision — "of what it shows, how much is right" — yes; recall
— "of what's really out there, how much did it catch" — no), not
something planned to be fixed here.

The other half is capturing your own judgment. Every job card on the
dashboard has three actions now, not two:

- **✓ Applied** — genuine match, you pursued it.
- **Not Interested** — a personal pass. Says nothing about whether the
  classification was *right* — could be a perfectly good KM/Legal-AI
  match you're skipping for an unrelated reason (location, comp,
  whatever). Deliberately excluded from precision math for exactly that
  reason.
- **✗ False Positive** — the scraper was wrong to classify this as
  auto-match/review at all. This is what precision gets computed from,
  alongside Applied.

Clicking a status button stores `{status, firm, title, verdict_at}` in
`localStorage` under the `lfcr_posting_status` key, captured at the moment
you click — not looked up later, since a posting can eventually stop
appearing in future dashboard runs (job closes, scraper drops it) and by
then there'd be nothing left to look up. Clicking "Export verdicts" (next
to "Show dismissed") copies every recorded verdict as a JSON array to your
clipboard, ready to paste into chat.

This is a single-device, browser-only store — it doesn't sync across
computers or browsers, and clearing browser data clears it. Getting the
verdicts *out* of the browser and into a durable, comparable form
(`data/eval_verdicts.jsonl`, merged against the predictions log to
actually compute precision) is the last remaining piece, not built yet.

One implementation detail worth knowing if you ever poke at
`lfcr_posting_status` in dev tools: this status shape (an object with
firm/title/verdict_at) replaced an earlier version that stored just a bare
status string (`"applied"`). The dashboard migrates old entries to the new
shape automatically the first time it loads after this change, so
existing Applied/Not Interested marks from before this update aren't
lost — but it's the reason the code has a migration step at all, in case
that ever looks like unnecessary complexity later.

## Automation

`.github/workflows/scrape.yml` runs the scraper twice daily (8am/4pm
Central, cron `0 13,21 * * *` — fixed UTC-6 offset, drifts an hour during
Central Daylight Time) plus on manual dispatch. It installs dependencies,
runs `python -m scraper.main`, dumps the console output to the job
summary, uploads `debug_all_titles.txt` as a build artifact, and commits
`data/seen_postings.json` + `report.html` + `index.html` back to the repo
if anything changed.

The report is published via GitHub Pages (Settings → Pages → Source →
"Deploy from a branch" → this branch → `/ (root)`, already enabled) at
https://sykotikgith.github.io/law-firm-career-radar/ — it auto-redeploys
whenever `report.html`/`index.html` change on the branch, so it reflects
whatever the most recent scheduled or manually-triggered run committed.
