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
    CustomHTMLAdapter,
    GreenhouseAdapter,
    ICIMSAdapter,
    OracleRecruitingAdapter,
    WorkdayAdapter,
)

FIRMS: dict[str, dict] = {
    # --- iCIMS group ---------------------------------------------------
    "Lewis Brisbois": {
        "adapter": ICIMSAdapter,
        "tenant": "lewisbrisbois",
        "search_url": "https://careers-lewisbrisbois.icims.com/jobs/search?pr=0&in_iframe=1",
        "notes": "CONFIRMED BLOCKED via live probe (both /jobs/intro and /jobs/search returned "
        "405 with an AWS WAF 'Human Verification' challenge page, not a URL/method problem). "
        "This tenant cannot be scraped with a plain HTTP client -- needs real browser "
        "automation (Playwright solving the WAF JS challenge) or manual checking.",
    },
    "Gordon Rees Scully Mansukhani": {
        "adapter": ICIMSAdapter,
        "tenant": "grsm",
        "search_url": "https://careers-grsm.icims.com/jobs/search?pr=0&in_iframe=1",
        "notes": "CONFIRMED BLOCKED via live probe -- same AWS WAF 'Human Verification' "
        "challenge as Lewis Brisbois. Not scrapable with a plain HTTP client.",
    },
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
    "Marshall Dennehey": {
        "adapter": CustomHTMLAdapter,
        "list_url": "https://www.marshalldennehey.com/careers/administrative-professionals",
        # Deliberately a selector that can't match anything real: this page has no job
        # listings (see notes), only nav links back to /careers/*. A broader selector like
        # "a[href*='/careers/']" was confirmed to scrape those nav links as fake "postings"
        # instead of returning the honest zero-results state.
        "link_selector": "a.job-posting-title",
        "notes": "NOT SCRAPABLE, needs manual periodic check instead. Confirmed via live "
        "probe: /careers/current-openings 404s; the sitemap (884KB, 4498 URLs) has zero "
        "individual job-posting URLs, only marketing landing pages (/careers, /attorneys, "
        "/summer-associates, /paralegals, /administrative-professionals); and the "
        "administrative-professionals page itself has no listings, just 'Submit your resume "
        "today to be considered for any of our current administrative positions.' This firm "
        "may not run an online job board for staff/business-professional roles at all -- "
        "treat as a manual-check firm, not an automatable one, until evidence says otherwise.",
    },
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
        # NOT a bespoke custom site -- confirmed Oracle PeopleSoft HCM (Candidate Gateway).
        "adapter": CustomHTMLAdapter,
        "list_url": "https://careers.reedsmith.com/jobs/vacancy/find/results",
        "link_selector": "a[href*='JobOpeningId']",
        "notes": "Confirmed backend is Oracle PeopleSoft HCM Recruiting (Fluid Candidate "
        "Gateway) at recruit.reedsmith.com, with numeric JobOpeningId identifiers. "
        "careers.reedsmith.com/jobs/... is a front-end search/results layer over that backend; "
        "unclear if it's server-rendered or JS-driven -- verify before trusting CustomHTMLAdapter "
        "here, may need a PeopleSoft-specific adapter instead.",
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
    "Orrick": {
        # Confirmed iCIMS (vanity domain talent.orrick.com fronts careers-orrick.icims.com).
        "adapter": ICIMSAdapter,
        "tenant": "orrick",
        "search_url": "https://careers-orrick.icims.com/jobs/search?pr=0&in_iframe=1",
        "notes": "Confirmed iCIMS tenant 'orrick'. CONFIRMED BLOCKED via live probe -- same "
        "AWS WAF 'Human Verification' challenge as Lewis Brisbois/GRSM. Not scrapable with a "
        "plain HTTP client. Public-facing vanity front-end is talent.orrick.com, with separate "
        "tracks: talent.orrick.com/staff-us/jobs (business professional -- the relevant one), "
        "/non-partner-attorney-us/jobs, /campus-us/jobs -- worth checking manually.",
    },
}
