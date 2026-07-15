# Squirrel Notes

Not things to build next. Things Future Maegan shouldn't have to remember.

## Parked ideas

**Repo/project rename** — DONE (2026-07-13)
Renamed from "LawFirmScraper" to "Law Firm Career Radar" (repo slug:
`law-firm-career-radar`, GitHub repo itself renamed via Settings →
General → Repository name — confirmed done). Live dashboard URL:
https://sykotikgith.github.io/law-firm-career-radar/ — confirmed working.
Dashboard page title/header, README title/intro, and this note all
updated to match. The Actions workflow (`scrape.yml`) needed no changes
— it never referenced the old repo name anywhere.

**Multi-user profiles**
YAML per person (e.g. `profiles/maegan.yaml`, `profiles/aly.yaml`), one scraping
engine, swappable keyword lens. Good architecture, deferred until the core is fully
proven for me. Needs per-profile state tracking, per-profile hosting, and a real
privacy conversation before adding anyone else's search activity to a public repo.

**Match scoring/weighting**
Explicitly rejected for now. Fake precision at current volume (~9 matches/run).
Revisit only if match volume grows substantially (post-AmLaw 200, maybe).

**Historical trend metrics**
Jobs by category over time, etc. Needs weeks of accumulated run history to mean
anything. Not viable yet. Revisit in a couple months once there's real history.

**AmLaw 200 expansion**
Deferred until AmLaw 100 is fully scoped with the pipeline-health dashboard in
place. Diminishing returns risk: smaller firms, less KM/AI infrastructure investment.

**iCIMS WAF block**
Lewis Brisbois, Gordon Rees, Orrick, Milbank all blocked by AWS WAF bot challenge.
Currently flagged "manual check needed" (Option 3 from our discussion). Playwright/
browser automation would unblock it, one-time cost that pays off across every
iCIMS tenant at once. Not urgent, easy to revisit if the need arises.

## From ChatGPT review session (accepted items)

**"New Since Last Run" section**
Add a dedicated section at the top of the dashboard showing only postings new
since the last run, separate from the full Auto-match/Review-manually lists.
Cheap to build since dedup/state tracking already exists — just needs a
filtered view. Once match volume grows, "what changed" matters more than
"everything available."

**Move diagnostics off the main dashboard**
The "Needs Manual Check" section (28 entries of dense technical prose) is
currently dominating the page below only 20 actual job matches — backwards
for a tool meant to answer "what should I look at today." Move to a
collapsible section or a separate diagnostics page. Fold in the redundant
"Firm Intelligence"/"Scraper Health Dashboard" ideas here too — same concept,
one page, not two.

**Coverage metrics**
Add a simple breakdown to the summary metrics: firms tracked / automated /
partial coverage / manual. Cheap, mostly just recounting what's already
tracked internally.

**Location filtering**
Not hypothetical — Norton Rose Fulbright's UK-based Newcastle postings are
currently mixed into regular Auto-match results with no way to distinguish
them from US postings without clicking through. Add a filter: All Locations /
US Only / Remote, etc.

**Rename "Review manually" vs. "Needs Manual Check"**
These two labels sound too similar even though they mean different things
(one's about the job title needing a judgment call, one's about the scraper's
technical reach). Consider clearer labels, e.g. "Potential Matches — needs
your judgment" vs. "Manual Firm Check — scraper can't reach this firm."

**Rejected / already covered, not re-adding:**
- "Match Reason Display" — already exists as the keyword pill tags on every
  card, just a different visual format than what was suggested.
- Historical trend tracking — same call as before, not enough accumulated
  run history yet to be meaningful.
- Multi-profile architecture — good design, independently re-suggested here,
  but the deferral reasons (per-profile state tracking, per-profile hosting,
  a real privacy conversation with Aly before her searches sit in a public
  repo) haven't changed.
- AmLaw 50/100 quick filters — fine later, not urgent for a single-user tool.

**Product philosophy worth keeping around**
Every feature should answer one of two questions: (1) what jobs should I look
at today, and (2) how confident am I that I'm seeing everything important.
If it doesn't serve one of those, it's lower priority.

## In progress (as of this note)

- AmLaw 100 expansion, Wave 1 (firms I've personally supported) then Wave 2
- Remote/hybrid/onsite detection and hard-exclude for onsite/hybrid
- Pipeline health dashboard (adapter failures, manual-review firms, no-postings firms)
- Playwright integration underway for JS-rendering-only Manual Check firms
  (Category 1), bot-protection firms (Category 2) being attempted as a
  secondary pass
