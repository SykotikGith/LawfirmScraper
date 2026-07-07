# LawfirmScraper

Scrapes career sites at 17 law firms for open business-professional roles in
IT, Knowledge Management, Legal AI, and related areas, and reports new
postings since the last run.

## Usage

```bash
pip install -r requirements.txt
python -m scraper.main          # scrape + report, remembering what's been seen
python -m scraper.main --reset-seen   # report every current match as "new"
```

Results are printed per firm. A dedup store at `data/seen_postings.json`
tracks posting IDs already reported so subsequent runs only flag genuinely
new postings.

## Filters

Include (any match keeps the posting): IT, Information Technology, Knowledge
Management, KM, AI Enablement, Legal AI, Application Support, IAM, Identity
and Access Management, Process Improvement, Innovation.

Exclude (any match drops the posting): attorney, associate, paralegal, legal
secretary, network engineer, on-call, 24/7, healthcare/clinical roles, and
"Manager" titles that aren't "IT Manager".

See `scraper/filters.py` to adjust.

## Firm coverage

See `scraper/config.py` for the full list of firms, their ATS platform, and
adapter configuration. Adapters live in `scraper/adapters/` — one per ATS
type (iCIMS, Workday, Oracle Recruiting Cloud, ApplicantStack, and a generic
custom-HTML adapter for bespoke career sites).

Some firms' career sites sit behind bot-protection (Akamai/WAF) that blocks
plain HTTP scraping; where that's the case it's noted in `config.py` and the
adapter may need a real browser-driven fetch (e.g. Playwright) instead of
`requests`.
