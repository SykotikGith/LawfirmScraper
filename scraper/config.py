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
        "notes": "Confirmed iCIMS tenant. Site returned 403 to sandboxed fetch (Akamai/WAF) "
        "during research; verify with a browser-realistic UA before trusting empty results.",
    },
    "Gordon Rees Scully Mansukhani": {
        "adapter": ICIMSAdapter,
        "tenant": "grsm",
        "search_url": "https://careers-grsm.icims.com/jobs/search?pr=0&in_iframe=1",
        "notes": "Confirmed iCIMS tenant. Same bot-protection caveat as Lewis Brisbois.",
    },
    "Wilson Elser": {
        # NOT iCIMS despite the original grouping guess -- confirmed custom site.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://www.wilsonelser.com/careers/professional_staff/current-opportunities",
        "link_selector": "a[href*='/job_openings/']",
        "notes": "Research found NO icims.com reference for this firm -- it runs a bespoke "
        "careers module at wilsonelser.com (job URLs like /careers/professional_staff/"
        "job_openings/{id}-{slug}). list_url is a best guess at the listing page for the "
        "business/professional-staff track and should be verified; attorney roles live "
        "under /careers/attorneys/job_openings/ and should stay excluded.",
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
            "recruitingCEJobRequisitions?onlyData=true&finder=findReqs;"
            "siteNumber=CX_1,limit=100"
        ),
        "job_url_template": (
            "https://hctq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/{id}"
        ),
        "notes": "Business-professionals careers page: cozen.com/careers/business-professionals. "
        "Confirmed Oracle Recruiting Cloud tenant (hctq / us2 / siteNumber CX_1) via indexed "
        "job URLs. Exact REST query params are the standard ORC convention, not captured "
        "live (site 403'd sandboxed fetch) -- verify response shape (items[0].requisitionList) "
        "on first real run and adjust OracleRecruitingAdapter parsing if the schema differs.",
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
        "list_url": "https://www.marshalldennehey.com/careers/current-openings",
        "link_selector": "a[href*='/careers/']",
        "notes": "Confirmed native CMS (no third-party ATS domain found) -- each posting is "
        "its own page at marshalldennehey.com/careers/<title-location-slug>. No IT/KM example "
        "posting was open during research; verify link_selector against live markup.",
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
        "wd": "wd1",
        "site": "perkinscoieexternal",
        "notes": "Ashurst and Perkins Coie completed a merger June 29, 2026, forming Ashurst "
        "Perkins Coie. Careers portal still runs under the legacy Perkins Coie Workday "
        "tenant as of this research (July 2026); no evidence of migration to a unified "
        "Ashurst-branded ATS yet. Re-verify tenant/site periodically as integration continues.",
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
        "list_url": "https://fisherphillips.hrmdirect.com/employment/job-openings.php",
        "link_selector": "a[href*='job-opening.php'], a[href*='view.php?req=']",
        "notes": "Confirmed ClearCompany/HRM Direct ATS at fisherphillips.hrmdirect.com "
        "(server-rendered PHP pages, no JSON feed). Business-professional roles are listed "
        "together with attorney/paralegal reqs in one feed, filterable by office -- rely on "
        "keyword filtering, not URL splitting. Example current posting: 'IT Application "
        "Specialist' (Atlanta).",
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
        "notes": "Confirmed iCIMS tenant 'orrick'. Public-facing vanity front-end is "
        "talent.orrick.com, with separate tracks: talent.orrick.com/staff-us/jobs (business "
        "professional -- the relevant one), /non-partner-attorney-us/jobs, /campus-us/jobs. "
        "The ICIMSAdapter here hits the underlying careers-orrick.icims.com search page "
        "directly, which lists all tracks together -- keyword filtering handles the split. "
        "Example current posting: 'IT Service Operations Intern' (Wheeling, WV).",
    },
}
