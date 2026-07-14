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
  data. Postings hard-excluded for being onsite/hybrid get an extra
  `-> excluded from ...` line explaining why.
- `report.html` / `index.html` — an identical static HTML report (see
  below), regenerated every run.

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
  in-office schedule ("3 days a week in office").
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
available for adapters that already fetch it as part of the data they'd
pull anyway, at no extra request cost: Greenhouse (`content=true` on the
existing API call), Oracle Recruiting Cloud (`WorkplaceType`/
`WorkplaceTypeCode` plus description fields), and viGlobal (trailing text
already present in the row it scrapes). Every other adapter — Workday,
Circa Works, ApplicantStack, and custom-HTML firms — detects from location
text alone, since fetching a full description would mean an extra HTTP
request per posting; those firms lean on "onsite"/"unclear" more often as
a result.

## Firm coverage

`scraper/config.py` has three top-level structures:

- `FIRMS` — the active, automated firm list (adapter class + tenant/URL
  config per firm). This is what `main.py` actually scrapes. Currently 53
  firms.
- `MANUAL_CHECK_FIRMS` — confirmed real target firms that can't be
  reliably automated (blocked by bot protection, no ATS trace in static
  HTML anywhere discoverable via sitemap search, a real ATS exists but
  requires authentication, or a real ATS exists but has no relevant
  listings). Not scraped; printed as a reminder list at the end of every
  run instead, with a check URL and the reason. Currently 34 firms,
  split into two tiers: confirmed genuine technical obstacles
  (WAF/bot-protection, credential-gated API, or a JS-rendered page with a
  confirmed real ATS/tenant underneath) versus unresearched leads (no
  confirmed block, no confirmed absence of postings either) still
  awaiting a fresh look.
- `REJECTED_LEADS` — slug guesses that turned out to be a different,
  unrelated company on a shared ATS platform (confirmed via real sample
  titles), kept on record so they aren't accidentally retried. Currently 2
  entries.

Adapters live in `scraper/adapters/` — one per ATS platform: iCIMS,
Workday (23 firms), Oracle Recruiting Cloud (2 firms), ApplicantStack, Greenhouse (2
firms), Circa Works, viGlobal (6 firms), UKG/UltiPro Recruiting (4 firms),
PageUp/eArcu, Jobvite, Breezy HR, Radancy, and a generic custom-HTML adapter (10 firms) for
bespoke career sites. (The iCIMS adapter exists but currently has no
active `FIRMS` entries — every iCIMS tenant found so far sits behind an
AWS WAF challenge and lives in `MANUAL_CHECK_FIRMS` instead.)

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
on every run: a metrics row (new matches, firms scanned, needs review,
last run time), an auto-match section, and a review-manually section,
each posting card linking straight to the real job listing. Each card
shows keyword-match pills, a work-arrangement pill ("Remote" or "remote
status unclear — verify" — see the work-arrangement filter above) in the
same monospace pill style, and a rotated "NEW" badge for postings not
seen on a previous run. Empty sections show a plain "no matches this run"
message. All scraped text is treated as untrusted and HTML-escaped before
rendering.

A third section, "Needs Manual Check" (amber accent), lists every firm
the scraper couldn't reach automatically — combining `MANUAL_CHECK_FIRMS`
(the permanent, documented list: WAF blocks, SPA-only sites, no
discoverable ATS, etc.) with any active `FIRMS` entry whose adapter
failed or returned zero postings *this specific run* (which might be
transient, or might be the first sign a site changed structure). Each
card shows the firm name, the specific reason, and a direct link to the
firm's careers page or main site to check by hand — this is what used to
only be visible in raw console output/job summary.

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
