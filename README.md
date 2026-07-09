# LawfirmScraper

Scrapes career sites at law firms for open business-professional roles in
IT, Knowledge Management, Legal AI, and related areas, classifies each
posting into auto-match / needs-review / excluded, tracks what's already
been seen, and publishes a static HTML report. Runs on a schedule via
GitHub Actions.

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
- `debug_all_titles.txt` — every scraped title (`Firm | Title | URL`,
  matched or not), for tuning the filter keywords against real data.
- `report.html` / `index.html` — an identical static HTML report (see
  below), regenerated every run.

## Filters

`scraper/filters.py` sorts every scraped title into one of four tiers, in
this order:

1. **Excluded** — a hard-exclude term is present (`HARD_EXCLUDE_TERMS`):
   Aderant, IT Asset (+ Specialist/Lead), Network Engineer, Engineering
   Manager, Development Manager, Finance/Financial/Billing/Accounting/
   Accountant, and JD/bar-required or support-staff titles (Attorney,
   Lawyer, Associate, Paralegal, Legal Secretary, Of Counsel, Partner).
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

## Firm coverage

`scraper/config.py` has three top-level structures:

- `FIRMS` — the active, automated firm list (adapter class + tenant/URL
  config per firm). This is what `main.py` actually scrapes.
- `MANUAL_CHECK_FIRMS` — confirmed real target firms that can't be
  reliably automated (blocked by bot protection, no ATS trace in static
  HTML, or a real ATS exists but has no relevant listings). Not scraped;
  printed as a reminder list at the end of every run instead, with a
  check URL and the reason.
- `REJECTED_LEADS` — slug guesses that turned out to be a different,
  unrelated company on a shared ATS platform (confirmed via real sample
  titles), kept on record so they aren't accidentally retried.

Adapters live in `scraper/adapters/` — one per ATS platform: iCIMS,
Workday, Oracle Recruiting Cloud, ApplicantStack, Greenhouse, Circa Works,
viGlobal, and a generic custom-HTML adapter for bespoke career sites.
(The iCIMS adapter exists but currently has no active `FIRMS` entries —
every iCIMS tenant found so far sits behind an AWS WAF challenge and
lives in `MANUAL_CHECK_FIRMS` instead.)

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
each posting card linking straight to the real job listing. Empty
sections show a plain "no matches this run" message. All scraped text is
treated as untrusted and HTML-escaped before rendering.

## Automation

`.github/workflows/scrape.yml` runs the scraper twice daily (8am/4pm
Central, cron `0 13,21 * * *` — fixed UTC-6 offset, drifts an hour during
Central Daylight Time) plus on manual dispatch. It installs dependencies,
runs `python -m scraper.main`, dumps the console output to the job
summary, uploads `debug_all_titles.txt` as a build artifact, and commits
`data/seen_postings.json` + `report.html` + `index.html` back to the repo
if anything changed.

For the HTML report to be viewable at a stable URL (e.g. from a phone),
enable GitHub Pages once in repo Settings → Pages → Source → "Deploy from
a branch" → this branch → `/ (root)`. GitHub Pages requires that manual,
repo-owner opt-in; there's no API bypass.
