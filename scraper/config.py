"""Per-firm scrape configuration.

Each entry maps a firm's display name to the adapter class that knows how
to talk to its ATS, plus adapter-specific config (tenant IDs, URLs, etc).

Endpoints below were identified via manual research of each firm's public
careers site (July 2026). Several career sites sit behind bot-protection
(Akamai/WAF) that returns 403 to naive HTTP clients — those are flagged
with a `notes` field. If an adapter starts failing, check whether the site
now requires a browser-driven fetch (e.g. Playwright with a real UA) rather
than plain `requests`, before assuming the tenant/site IDs are wrong.
"""
from __future__ import annotations

from .adapters import (
    ApplicantStackAdapter,
    CircaWorksAdapter,
    CustomHTMLAdapter,
    EArcuAdapter,
    GreenhouseAdapter,
    JobviteAdapter,
    OracleRecruitingAdapter,
    UltiProAdapter,
    ViGlobalAdapter,
    WorkdayAdapter,
)

FIRMS: dict[str, dict] = {
    # --- iCIMS group ---------------------------------------------------
    # Lewis Brisbois and Gordon Rees Scully Mansukhani dropped per explicit request -- both
    # were confirmed iCIMS tenants (lewisbrisbois, grsm) blocked by the same AWS WAF
    # "Human Verification" challenge as Milbank/Orrick, never scrapable with a plain HTTP
    # client.
    "Wilson Elser": {
        # NOT iCIMS, and NOT the bespoke HTML site originally guessed either -- confirmed
        # Greenhouse via live probe (the site is a bare React SPA with no server-rendered
        # content; its JS bundle references the Greenhouse public boards API directly).
        "adapter": GreenhouseAdapter,
        "board_token": "wilsonelser",
        "notes": "CONFIRMED via live probe: wilsonelser.com/careers is a client-side-only "
        "React app (Great Jakes CMS) that calls "
        "https://boards-api.greenhouse.io/v1/boards/wilsonelser/jobs?content=true directly -- "
        "a clean public JSON API, no HTML scraping needed. Greenhouse doesn't distinguish "
        "attorney vs business-professional roles at the API level -- rely on keyword "
        "filtering.",
    },
    # --- Workday group ---------------------------------------------------
    "DLA Piper": {
        "adapter": WorkdayAdapter,
        "tenant": "dlapiper",
        "wd": "wd1",
        "site": "dlapiper",
        "notes": "Confirmed Workday tenant via indexed job URLs. JSON API endpoint pattern "
        "is the standard Workday CXS convention, not directly hit during research "
        "(sandbox network blocked *.myworkdayjobs.com) -- verify a GET to the HTML "
        "careers page succeeds before the POST (Workday sometimes needs session cookies).",
    },
    "Clyde & Co US": {
        "adapter": WorkdayAdapter,
        "tenant": "clydeco",
        "wd": "wd103",
        "site": "clydecocareers",
        "notes": "Confirmed Workday tenant, but example postings found were UK/global "
        "(London, Dubai, Montreal) -- this may be one global Workday site rather than a "
        "US-only tenant. Filter/verify by location text for 'US' postings specifically.",
    },
    # --- Oracle-style group ---------------------------------------------------
    "Cozen O'Connor": {
        "adapter": OracleRecruitingAdapter,
        "api_url": (
            "https://hctq.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/"
            "recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
            "&finder=findReqs;siteNumber=CX_1,limit=100"
        ),
        "job_url_template": (
            "https://hctq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/{id}"
        ),
        "notes": "Business-professionals careers page: cozen.com/careers/business-professionals. "
        "Confirmed Oracle Recruiting Cloud tenant (hctq / us2 / siteNumber CX_1). CONFIRMED via "
        "live probe: without expand=requisitionList the API returns only a facets echo "
        "(TotalJobsCount populated but no job list) -- fixed by adding that query param. "
        "Still need to verify the exact field names inside requisitionList entries match "
        "OracleRecruitingAdapter's assumptions (Id/Title/PrimaryLocation).",
    },
    "Baker McKenzie": {
        # NOT Oracle/Taleo despite the original grouping guess -- confirmed Avature.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://careers.bakermckenzie.com/en_US/opportunities/SearchJobs",
        "link_selector": "a[href*='/JobDetail/']",
        "notes": "Confirmed Avature ATS (careers.bakermckenzie.com), not Oracle. No public "
        "JSON API found. SearchJobs listing may render via JS -- if CustomHTMLAdapter "
        "returns nothing, the page likely needs a browser-driven fetch rather than a "
        "plain GET. No US-vs-global or business-services-vs-attorney URL split confirmed; "
        "verify category filtering is needed once the page is reachable.",
    },
    # --- ApplicantStack ---------------------------------------------------
    "Hinshaw & Culbertson": {
        "adapter": ApplicantStackAdapter,
        "board_url": "https://hinshawlaw.applicantstack.com/x/openings",
        "link_selector": "a[href*='/x/detail/']",
        "notes": "Confirmed ApplicantStack tenant 'hinshawlaw'. Job detail URLs look like "
        "/x/detail/<jobid>. No public JSON feed found -- HTML scrape only. Example current "
        "posting seen during research: 'Senior IT Systems & Infrastructure Engineer'.",
    },
    # --- Custom / structured ---------------------------------------------------
    "Goldberg Segalla": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://www.goldbergsegalla.com/our-story/career-opportunities-at-goldberg-segalla/",
        "link_selector": "a[href*='/opportunities/']",
        "notes": "Weakest-verified entry: no third-party ATS domain found, but listings appear "
        "split across per-state landing pages (.../opportunities/new-york/, /new-jersey/, etc.) "
        "rather than one flat list -- this adapter config likely needs per-state list_urls once "
        "verified, not a single page.",
    },
    "Reed Smith": {
        # CORRECTION (July 2026, live diagnostics): the original "Oracle PeopleSoft at
        # recruit.reedsmith.com" note was wrong -- that host doesn't even resolve (DNS
        # failure). Confirmed via live probe to actually be PageUp/eArcu (meta
        # name="author" content="PageUp Europe", earcu-details meta tag) -- a platform not
        # seen anywhere else in this project, needing its own EArcuAdapter (the list page is
        # a JS shell; real data loads via an AJAX grid endpoint after page load).
        "adapter": EArcuAdapter,
        "list_url": "https://careers.reedsmith.com/jobs/vacancy/find/results",
        "notes": "CONFIRMED via live probing (4 diagnostic rounds) -- 54 real postings across "
        "5 pages, sample titles unmistakably genuine ('Business Development Coordinator', "
        "'Conflicts & Risk Management Attorney', 'Corporate Securities Paralegal', all with "
        "plausible real office locations). EArcuAdapter primes a session against list_url to "
        "get a live pagestamp token + session cookies, then sweeps the AJAX grid endpoint "
        "(ajaxaction/posbrowser_gridhandler) page by page until an empty page -- verified "
        "end-to-end against all 54 postings with zero duplicates. No full description text "
        "available in the grid response, so work-arrangement detection here relies on "
        "location text alone.",
    },
    # --- Recently merged, verify structure ---------------------------------------------------
    "Ashurst Perkins Coie (fka Perkins Coie)": {
        "adapter": WorkdayAdapter,
        "tenant": "perkinscoie",
        "wd": "wd115",
        "site": "perkinscoieexternal",
        "notes": "Ashurst and Perkins Coie completed a merger June 29, 2026, forming Ashurst "
        "Perkins Coie. Careers portal still runs under the legacy Perkins Coie Workday "
        "tenant as of this research (July 2026); no evidence of migration to a unified "
        "Ashurst-branded ATS yet. Re-verify tenant/site periodically as integration continues. "
        "CONFIRMED via live probe: pod is wd115 (wd1 and wd5 both 422); 47 jobs live.",
    },
    # --- Still need ATS ID -- resolved via research ---------------------------------------------------
    "Tucker Ellis": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://www.tuckerellis.com/careers/",
        "link_selector": "a.job-title, a[href*='/careers/']",
        "notes": "ATS platform UNCONFIRMED -- no search evidence ties this firm to any named "
        "ATS vendor; the page may embed a widget/iframe. list_url/link_selector are guesses "
        "against the marketing page and must be verified directly (view page source for an "
        "iframe src or embedded script pointing at an ATS domain) before this adapter will work.",
    },
    "Fisher Phillips": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://fisherphillips.hrmdirect.com/employment/job-openings.php?search=true&state=-1&office=-1",
        "link_selector": "a[href*='job-opening.php?req=']",
        "notes": "Confirmed ClearCompany/HRM Direct ATS at fisherphillips.hrmdirect.com "
        "(server-rendered PHP pages, no JSON feed). CONFIRMED via live probe: job-openings.php "
        "is a search FORM, not a static list -- it shows 'Select options... and click Search' "
        "until submitted. list_url now submits the form with default/empty filters "
        "(search=true&state=-1&office=-1), which returns 46 real job links "
        "(job-opening.php?req=<id>&req_loc=<locid>). Same req can appear multiple times with "
        "different req_loc for multi-location postings -- expect occasional duplicate titles, "
        "each a distinct location listing rather than a scraper bug. Business-professional "
        "roles are listed together with attorney/paralegal reqs -- rely on keyword filtering, "
        "not URL splitting. Example current posting: 'IT Application Specialist' (Atlanta).",
    },
    "Seyfarth Shaw": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://careers.seyfarth.com/jobs",
        "link_selector": "a[href*='/jobs/']",
        "notes": "ATS vendor UNCONFIRMED (career site migrated off recruiting.seyfarth.com at "
        "some point) but URL pattern is stable: careers.seyfarth.com/jobs/<numeric-id>. "
        "Business-professional and attorney roles are listed together in one feed -- rely on "
        "keyword filtering. Example current posting seen: 'Director of Knowledge Management' "
        "(Office of General Counsel, Wilmington DE, hybrid) -- a strong direct match.",
    },
    "Littler Mendelson": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://www.littler.com/careers/us/professional-staff",
        "link_selector": "a.job-title, a[href*='/careers/']",
        "notes": "ATS platform UNCONFIRMED -- no external ATS domain surfaced in research; "
        "likely an embedded widget/iframe on this page. list_url targets the professional-"
        "staff (non-attorney) track, which explicitly covers applications development and "
        "knowledge management disciplines. Verify page source for the real ATS/iframe target "
        "before trusting this adapter.",
    },
    # --- Batch 2: 69-firm expansion, resolved via ats_probe.py + verify_batch.py -----------
    "Simpson Thacher": {
        "adapter": WorkdayAdapter,
        "tenant": "stblaw",
        "wd": "wd1",
        "site": "careers",
        "notes": "CONFIRMED via live probe -- 63 real postings, sample titles unmistakably "
        "law-firm-specific ('Knowledge Management Lawyer - Energy & Infrastructure', 'Senior "
        "AI Enablement & Adoption Analyst' -- direct hits on target roles). Note the slug "
        "guess 'simpsonthacher' is NOT the real tenant -- it's 'stblaw'.",
    },
    "Greenberg Traurig": {
        "adapter": WorkdayAdapter,
        "tenant": "gtlaw",
        "wd": "wd1",
        "site": "gtlaw",
        "notes": "CONFIRMED via live probe -- 249 real postings, sample titles unmistakably "
        "law-firm-specific ('Trademark Paralegal', 'Corporate M&A Associate', 'Innovation "
        "Manager, Applied AI').",
    },
    "King & Spalding": {
        "adapter": WorkdayAdapter,
        "tenant": "kslaw",
        "wd": "wd1",
        "site": "careers",
        "notes": "CONFIRMED via live probe -- 36 real postings, sample titles plausibly "
        "law-firm business-professional roles ('Paralegal', 'Business Development Manager').",
    },
    "Gibson Dunn": {
        "adapter": GreenhouseAdapter,
        "board_token": "gibsondunn",
        "notes": "CONFIRMED via live probe -- 89 real postings, 'Assistant Litigation Docket "
        "Manager' confirms this is genuinely the law firm, not a slug collision with an "
        "unrelated company on Greenhouse.",
    },
    "Goodwin Procter": {
        "adapter": WorkdayAdapter,
        "tenant": "goodwinprocter",
        "wd": "wd5",
        "site": "External_Careers",
        "notes": "CONFIRMED via live probe -- 44 real postings. This is Workday, NOT the "
        "Greenhouse 'goodwin' board_token ats_probe.py originally found (that was a false "
        "collision with an unrelated company, same shape as Winston & Strawn's -- see "
        "rejected list below). Real endpoint found embedded directly in "
        "goodwinlaw.com/en/careers, on pod wd5 which wasn't even in ats_probe.py's original "
        "wd1/wd103/wd115 list. 'eDiscovery Project Manager (Relativity certification "
        "required)' confirms genuine law-firm identity -- Relativity is eDiscovery software "
        "specifically used by law firms.",
    },
    "Alston & Bird": {
        "adapter": WorkdayAdapter,
        "tenant": "alston",
        "wd": "wd1",
        "site": "ExternalCareer",
        "notes": "CONFIRMED via live probe -- 23 real postings, found embedded directly in "
        "alston.com/careers. Direct hit on target roles: 'Legal AI Solutions Analyst'.",
    },
    "Holland & Knight": {
        "adapter": WorkdayAdapter,
        "tenant": "hklaw",
        "wd": "wd1",
        "site": "Holland_Knight",
        "notes": "CONFIRMED via live probe -- 89 real postings, found embedded directly in "
        "hklaw.com/careers. Sample titles plausibly law-firm business-professional roles "
        "('Business Development Coordinator', 'Practice Assistant - Labor & Employment').",
    },
    "Paul Hastings": {
        "adapter": WorkdayAdapter,
        "tenant": "paulhastings",
        "wd": "wd1",
        "site": "PH-Staff",
        "notes": "CONFIRMED via live probe -- 29 real postings, plausible business-"
        "professional titles ('Senior IT Project Manager', 'Senior Integration Engineer').",
    },
    "Cooley": {
        "adapter": WorkdayAdapter,
        "tenant": "cooley",
        "wd": "wd1",
        "site": "Cooley_US_LLP",
        "notes": "CONFIRMED via live probe -- 87 real postings, unmistakably law-firm-"
        "specific titles ('Conflicts Staff Attorney', 'Senior Practice Innovation Manager', "
        "'Litigation Marketing Senior Manager').",
    },
    "Jackson Lewis": {
        "adapter": WorkdayAdapter,
        "tenant": "jacksonlewis",
        "wd": "wd1",
        "site": "JacksonLewisBusinessandLegalProfessionalsCareers",
        "notes": "CONFIRMED via live probe -- 113 real postings, unmistakably law-firm-"
        "specific titles ('Litigation Paralegal', '2027 Summer Associate', 'Legal Secretary').",
    },
    "Debevoise & Plimpton": {
        # NOT actually Workday for external postings, despite a real tenant existing on wd1
        # (confirmed via ats_probe.py's path-specific-error signal, which we verified is
        # reliable -- not a fluke). Likely a dormant/internal Workday tenant not used for
        # external recruiting. Real external ATS is Circa Works (circaworks.com /
        # LocalJobNetwork), a platform not seen anywhere else in this project.
        "adapter": CircaWorksAdapter,
        "list_url": "https://employer.circaworks.com/s/e-Debevoise-Plimpton-LLP-jobs-e87905.html?pbid=68216",
        "notes": "CONFIRMED via live probe -- 14 real postings found, title/location encoded "
        "directly in each job link's URL slug rather than relying on unverified anchor text. "
        "Direct hit on target roles: 'AI Business Systems Developer'. Job links use a "
        "javascript: self.popup(...) pseudo-href rather than a plain <a href> URL -- "
        "CircaWorksAdapter regexes the real path out of the popup() call.",
    },
    "O'Melveny & Myers": {
        # NOT actually Workday for external postings, despite a real tenant existing on wd1
        # (confirmed via ats_probe.py's verified path-specific-error signal) -- same pattern
        # as Debevoise & Plimpton: likely a dormant/internal Workday tenant. Real external ATS
        # is viGlobal/viRecruit (viglobalcloud.com), a legal-industry-specific platform not
        # seen anywhere else in this project.
        "adapter": ViGlobalAdapter,
        "list_url": "https://ommcareers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx"
        "?Tag=84c08942-ea6c-4707-a535-258e400c6b3d",
        "notes": "CONFIRMED via live probe -- 49 real postings server-rendered directly in an "
        "ASP.NET GridView table (id=contentPlaceHolder_gridviewList), no separate API call "
        "needed. Per-job 'Apply' controls are ASP.NET postback LinkButtons "
        "(javascript:__doPostBack(...)), not real navigable URLs, so ViGlobalAdapter regexes "
        "title/office/group/date directly out of each row's concatenated cell text instead, "
        "and every posting shares the same list_url since there's no per-job URL to link to. "
        "Sample titles found: 'Assistant' (Dallas), 'Billing and Collections Coordinator' "
        "(multiple offices) -- plausible law-firm business-professional roles.",
    },
    "White & Case": {
        "adapter": WorkdayAdapter,
        "tenant": "whitecase",
        "wd": "wd1",
        "site": "External",
        "notes": "CONFIRMED via live probe -- 118 real postings. Front-end now redirects "
        "through the newer wd1.myworkdaysite.com/recruiting/whitecase/External domain, but "
        "the underlying CXS API at the old-style tenant subdomain "
        "(whitecase.wd1.myworkdayjobs.com/wday/cxs/whitecase/External/jobs) still works fine "
        "-- WorkdayAdapter needed no changes.",
    },
    "Troutman Pepper Locke": {
        # Locke Lord merged into Troutman Pepper Locke Jan 1, 2025. This entry supersedes
        # the separately-confirmed "lockelord" Workday tenant from ats_probe.py -- troutman's
        # own tenant is the one actually in use post-merger.
        "adapter": WorkdayAdapter,
        "tenant": "troutman",
        "wd": "wd5",
        "site": "TPRecruit1",
        "notes": "CONFIRMED via live probe -- 33 real postings, plausible law-firm titles "
        "('Legal Practice Assistant', 'Business Development Manager', 'Conflicts "
        "Researcher').",
    },
    "Fenwick & West": {
        "adapter": WorkdayAdapter,
        "tenant": "fenwick",
        "wd": "wd1",
        "site": "Fenwick_External_Careers",
        "notes": "CONFIRMED via live probe -- 35 real postings, unmistakably law-firm-"
        "specific titles ('Trademark Operations Supervisor', 'Senior Legal Support "
        "Analyst', 'Patent Client Services Administrator', 'Mid-Level Trademark "
        "Paralegal').",
    },
    "Haynes and Boone": {
        "adapter": WorkdayAdapter,
        "tenant": "haynesboone",
        "wd": "wd503",
        "site": "HaynesandBoone",
        "notes": "Tenant/pod/site and the full paging contract (POST body shape, "
        "offset/total behavior, title/locationsText/postedOn/externalPath field "
        "mapping) supplied directly from the user's own network inspection of the "
        "live API -- matches WorkdayAdapter's existing request/response handling "
        "exactly, no adapter changes needed.",
    },
    # --- UltiPro / UKG Recruiting group ---------------------------------------------------
    "Akerman": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting.ultipro.com/AKE1000ASEPA/JobBoard/"
        "b855fc7e-c6e0-90cc-b829-ddbebeb6f274/",
        "notes": "CONFIRMED via live probing (5 diagnostic rounds, since this sandbox has no "
        "outbound network access) -- 96 real postings across 5 pages, sample titles plausibly "
        "genuine ('Legal Administrative Assistant', 'Conflicts Analyst', 'Senior Competitive "
        "Intelligence Specialist' in Wilmington/West Palm Beach/Tampa/Miami/etc.). The board is "
        "a Knockout.js page, NOT the classic static-link template originally guessed -- real "
        "job data comes from POSTing {\"opportunitySearch\": {\"Text\": \"\", \"Skip\": N, "
        "\"Take\": 20}} to <board_url>JobBoardView/LoadSearchResults. Two quirks caught via "
        "live testing before trusting this: the server hard-caps page size to 20 regardless of "
        "the requested Take value, and the initially-guessed PageNumber/PageSize params were "
        "silently ignored (always returned the identical first 20) -- pagination is purely "
        "Skip-driven, verified end-to-end against all 96 postings with zero duplicates/gaps. "
        "No full description text available in the search response, so work-arrangement "
        "detection here relies on location text alone.",
    },
    # --- AmLaw 100 expansion batch, resolved via ats_probe.py + verify_batch.py -----------
    "Morgan Lewis": {
        "adapter": WorkdayAdapter,
        "tenant": "morganlewis",
        "wd": "wd5",
        "site": "morganlewis",
        "notes": "CONFIRMED via live probe -- 37 real postings, plausible law-firm "
        "business-professional titles ('Practice Group Support Assistant - Litigation', "
        "'Legal Practice Assistant - Investment Management', 'Litigation Docket Specialist', "
        "'Senior Client Employee Benefits Advisor').",
    },
    "Norton Rose Fulbright": {
        "adapter": WorkdayAdapter,
        "tenant": "nrf",
        "wd": "wd3",
        "site": "External",
        "notes": "CONFIRMED via live probe -- 126 real postings, found embedded directly in "
        "nortonrosefulbright.com/en-us/careers via the newer myworkdaysite.com front-end "
        "domain (same pattern as White & Case -- still routes to the standard old-style CXS "
        "API, no adapter changes needed). Sample titles include 'Executive, Billing "
        "Operations - EMEA (12-month FTC)' and 'Assistenz' (German for 'Assistant') -- this "
        "looks like ONE GLOBAL Workday tenant covering non-US offices too, same situation as "
        "Clyde & Co. Filter/verify by location text for US postings specifically if that "
        "matters; the existing keyword + work-arrangement filters don't currently do "
        "location-based country filtering.",
    },
    "Faegre Drinker": {
        "adapter": WorkdayAdapter,
        "tenant": "esswd",
        "wd": "wd501",
        "site": "External",
        "notes": "CONFIRMED via live probe -- 11 real postings, plausible/strong "
        "business-professional titles ('Director of AI & Automation', 'Senior Legal "
        "Solutions Designer', 'Director of Enterprise Data Management & Engineering', "
        "'Legal Administrative Assistant'). Tenant slug 'esswd' and pod 'wd501' are BOTH "
        "different from what ats_probe.py guessed ('faegredrinker' slug, wd1-wd10/103/115 "
        "pod range) -- found instead via the firm's own careers page embedding a Workday "
        "link directly. 'esswd' likely traces back to a predecessor entity name (Faegre "
        "Drinker formed from a 2020 Faegre Baker Daniels + Drinker Biddle & Reath merger).",
    },
    "Bryan Cave Leighton Paisner": {
        # Second viGlobal tenant found in this project (after O'Melveny & Myers), with a
        # DIFFERENT row template -- see viglobal.py's module docstring. ViGlobalAdapter
        # tries the structured <h4>/<h5> shape first, falls back to O'Melveny's
        # concatenated-text-blob shape, so one adapter covers both.
        "adapter": ViGlobalAdapter,
        "list_url": "https://bclplaw-careers.viglobalcloud.com/viRecruitSelfApply/RecDefault.aspx",
        "notes": "CONFIRMED via live probe -- the bare list_url (no query params) renders the "
        "real unfiltered listing directly, no Tag= GUID needed unlike O'Melveny's tenant. 5 "
        "rows total: 1 generic 'General Online Application' placeholder (harmless -- won't "
        "match any AI/KM keyword, silently dropped by the title filter) plus 4 real postings "
        "at time of verification, all attorney/associate roles ('Mergers and Acquisitions "
        "Associate, Atlanta', 'Mid to Senior Business & Commercial Disputes Associate - "
        "Dallas'). No description text available -- this template's description div is "
        "empty in server-rendered HTML (populated client-side after load).",
    },
    "Davis Wright Tremaine": {
        # New platform for this project: Jobvite. Looks like a client-side JS app from the
        # page shell but the job table itself is fully server-rendered -- see jobvite.py.
        "adapter": JobviteAdapter,
        "board_url": "https://jobs.jobvite.com/dwt/",
        "notes": "CONFIRMED via live probe -- 19 real postings, direct hits on target roles "
        "('AI Developer', 'eDiscovery Project Manager', 'Cybersecurity Analyst', 'Data "
        "Analyst - Class Action Defense'), plus plausible business-professional titles "
        "('Business Development Manager', 'Client Experience Legal Project Coordinator'). "
        "Real per-job URLs and locations both available directly in static HTML, no JS "
        "execution or extra requests needed despite the page initially looking like a "
        "client-side app.",
    },
}


# ---------------------------------------------------------------------------
# Firms requiring MANUAL CHECK -- confirmed real target firms that cannot be
# reliably automated (WAF/bot-blocked, no ATS trace in static HTML, or a
# real ATS exists but has no relevant listings). Not iterated by main.py --
# these are documented here (with whatever config data research turned up,
# in case a future fix becomes possible) rather than left as live FIRMS
# entries that fail every run.
# ---------------------------------------------------------------------------
MANUAL_CHECK_FIRMS: dict[str, dict] = {
    "Orrick": {
        "reason": "Confirmed iCIMS tenant 'orrick', but blocked by an AWS WAF 'Human "
        "Verification' challenge -- not scrapable with a plain HTTP client.",
        "tenant": "orrick",
        "search_url": "https://careers-orrick.icims.com/jobs/search?pr=0&in_iframe=1",
        "check_url": "https://talent.orrick.com/staff-us/jobs",
        "notes": "Public-facing vanity front-end is talent.orrick.com, with separate tracks: "
        "/staff-us/jobs (business professional -- the relevant one), "
        "/non-partner-attorney-us/jobs, /campus-us/jobs.",
    },
    "Milbank": {
        "reason": "Real ATS is iCIMS (found via the firm's own careers page), blocked by the "
        "same AWS WAF 'Human Verification' challenge as Orrick. A Workday tenant also exists "
        "on wd1 but is apparently dormant/internal, not used for external recruiting.",
        "tenant": "milbank",
        "search_url": "https://careers-milbank.icims.com/jobs/intro?hashed=-435594439",
    },
    "Marshall Dennehey": {
        "reason": "No scrapable job board found at all. /careers/current-openings 404s; the "
        "sitemap (884KB, 4498 URLs) has zero individual job-posting URLs, only marketing "
        "landing pages; and /careers/administrative-professionals has no listings, just "
        "'Submit your resume today...'. May not run an online job board for staff/"
        "business-professional roles at all.",
        "check_url": "https://www.marshalldennehey.com/careers/administrative-professionals",
    },
    "Ropes & Gray": {
        "reason": "ropesgray.com 403s on every path (bot protection), blocking the "
        "embedded-link-discovery technique used for every other firm here. A real "
        "ApplicantStack tenant may exist (ropesgray.applicantstack.com/x/openings returned "
        "0 postings), but that's not enough to confirm identity.",
        "check_url": "https://ropesgray.applicantstack.com/x/openings",
    },
    "Blank Rome": {
        "reason": "Real tenant confirmed on Workday wd1 (path-specific-error signal) but the "
        "site slug was never found -- the business-professionals careers page has zero ATS "
        "trace of any kind in its static HTML (no Workday link old or new format, no other "
        "known ATS domain, no search/openings-labeled links). Whatever renders the job list "
        "is pure client-side JS with no static fallback.",
        "check_url": "https://www.blankrome.com/careers/overview/business-professionals/",
    },
    "Covington & Burling": {
        "reason": "Real tenant confirmed on Workday wd1 (path-specific-error signal) but the "
        "site slug was never found -- the business-professionals page uses Coveo "
        "(static.cloud.coveo.com), an enterprise search layer on their Sitecore CMS, not a "
        "job board ATS directly. Job data is fetched via a JS search API call after page "
        "load, invisible to static HTML scraping.",
        "check_url": "https://www.cov.com/en/careers/business-professionals/employment-opportunities",
    },
    "Weil Gotshal": {
        "reason": "Checked manually -- no listings for business-professional/staff roles, "
        "only attorney postings. Not worth an adapter; there's nothing for our filters to "
        "find even if scraping worked.",
    },
    # --- AmLaw 100 expansion batch: real Workday tenants confirmed (path-specific-error
    # signal) but evidently dormant/internal, same pattern as Milbank above -- the real
    # external-recruiting site is a different platform or unreachable for a firm-specific
    # reason. -----------------------------------------------------------------------------
    "McDermott Will & Emery": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. mwe.com/careers redirects to mcdermottlaw.com/careers, "
        "which is blocked by an Imperva Incapsula bot-protection challenge -- not scrapable "
        "with a plain HTTP client, same category as iCIMS's AWS WAF block.",
        "check_url": "https://www.mcdermottlaw.com/careers",
    },
    "Morrison & Foerster": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. mofo.com/careers redirects to careers.mofo.com, a "
        "Next.js SPA with zero job data in static HTML -- the real ATS/API wasn't identified.",
        "check_url": "https://careers.mofo.com/",
    },
    "Skadden Arps": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. skadden.com/careers is an AngularJS SPA "
        "(ng-app=\"skadden\") with zero job data in static HTML.",
        "check_url": "https://www.skadden.com/careers",
    },
    "Davis Polk": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. The real careers path wasn't found -- "
        "davispolk.com/careers returns 403 (bot-protected) and the bare domain has no ATS "
        "trace.",
        "check_url": "https://www.davispolk.com",
    },
    "Hogan Lovells": {
        "reason": "Real tenant confirmed on Workday wd3 (path-specific-error signal), "
        "apparently dormant/internal. UNVERIFIED ODDITY: hoganlovells.com redirects to a "
        "completely different domain, hlc.com -- could be a legitimate rebrand or could be "
        "something else entirely; not confirmed as the same firm. No ATS trace found on "
        "that destination page either way. Needs a human to eyeball hlc.com before trusting "
        "it as Hogan Lovells' real site.",
        "check_url": "https://www.hlc.com/",
    },
    "Cleary Gottlieb": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. clearygottlieb.com/careers redirects to the bare "
        "homepage (Sitefinity CMS) -- the real careers subpage URL wasn't found.",
        "check_url": "https://www.clearygottlieb.com/careers",
    },
    "Nelson Mullins": {
        "reason": "Confirmed iCIMS tenant 'nelsonmullins' (found embedded in "
        "nelsonmullins.com/careers), blocked by the same AWS WAF 'Human Verification' "
        "challenge as Orrick/Milbank -- not scrapable with a plain HTTP client.",
        "tenant": "nelsonmullins",
        "search_url": "https://careers-nelsonmullins.icims.com/jobs/search",
        "check_url": "https://www.nelsonmullins.com/careers",
    },
    "Foley & Lardner": {
        "reason": "Confirmed iCIMS tenant 'foley' (found embedded in foley.com/careers), "
        "blocked by the same AWS WAF 'Human Verification' challenge as Orrick/Milbank -- "
        "not scrapable with a plain HTTP client.",
        "tenant": "foley",
        "search_url": "https://careers-foley.icims.com/jobs/intro?hashed=-626009846",
        "check_url": "https://www.foley.com/careers/",
    },
}

# ---------------------------------------------------------------------------
# Rejected leads: not target firms at all, just slug collisions on a shared
# platform host that were confirmed via real sample titles to belong to an
# unrelated company. Kept here so these guesses aren't accidentally retried.
# ---------------------------------------------------------------------------
REJECTED_LEADS: dict[str, str] = {
    "winston (HRMdirect)": "Guessed for Winston & Strawn -- confirmed collision. Sample "
    "titles ('R&D Culinary Technologist', 'Quality Assurance Inspector', 'Quality "
    "Engineering Manager') are food/manufacturing-industry titles. This tenant belongs to "
    "Winston Taylor (winstontaylor.com), an unrelated company.",
    "goodwin (Greenhouse board_token)": "Guessed for Goodwin Procter -- confirmed collision, "
    "same shape as Winston & Strawn's. Goodwin Procter's real ATS is Workday (see "
    "FIRMS['Goodwin Procter']); this Greenhouse tenant with its 1 thin, non-legal posting "
    "belongs to some other company.",
}
