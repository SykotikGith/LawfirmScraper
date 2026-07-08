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
    GreenhouseAdapter,
    ICIMSAdapter,
    OracleRecruitingAdapter,
    ViGlobalAdapter,
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
    "Milbank": {
        # NOT actually Workday for external postings, despite a real tenant existing on wd1
        # (confirmed via ats_probe.py's verified path-specific-error signal) -- same pattern
        # as Debevoise/O'Melveny: real external ATS is iCIMS, found via the firm's own
        # careers page. Same treatment as Lewis Brisbois/GRSM/Orrick.
        "adapter": ICIMSAdapter,
        "tenant": "milbank",
        "search_url": "https://careers-milbank.icims.com/jobs/intro?hashed=-435594439",
        "notes": "CONFIRMED BLOCKED via the same AWS WAF 'Human Verification' challenge as "
        "Lewis Brisbois/GRSM/Orrick -- not scrapable with a plain HTTP client.",
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
    # Firms probed but deliberately NOT added, pending more evidence or explicitly rejected:
    #
    # - Winston & Strawn (HRMdirect, winston.hrmdirect.com): REJECTED -- confirmed collision.
    #   Sample titles ("R&D Culinary Technologist", "Quality Assurance Inspector", "Quality
    #   Engineering Manager") are food/manufacturing-industry titles, not remotely
    #   law-firm-shaped. Confirmed: this "winston" tenant belongs to Winston Taylor
    #   (winstontaylor.com), an unrelated company -- not Winston & Strawn.
    #
    # - "Goodwin" Greenhouse board_token: REJECTED -- confirmed collision, same shape as
    #   Winston & Strawn's. Goodwin Procter's real ATS is Workday (see entry above); this
    #   Greenhouse tenant with its 1 thin, non-legal posting belongs to some other company.
    #
    # - Ropes & Gray (ApplicantStack, ropesgray.applicantstack.com/x/openings): DROPPED --
    #   ropesgray.com 403s on every path (bot protection), blocking the same
    #   embedded-link-discovery technique used for every other firm here. Explicit call not
    #   to keep pursuing this one.
    #
    # - Weil Gotshal: checked manually -- no listings for business-professional/staff roles,
    #   only attorney postings. Not worth an adapter; there's nothing for our filters to find
    #   even if scraping worked.
    #
    # - Blank Rome: DROPPED. Real tenant confirmed on Workday wd1 (path-specific-error
    #   signal) but the site slug was never found -- blankrome.com/careers/overview/
    #   business-professionals/ has zero ATS trace of any kind in its static HTML (no
    #   Workday link old or new format, no other known ATS domain, no
    #   search/openings-labeled links). Whatever renders the job list is pure client-side JS
    #   with no static fallback. Same category as Ropes & Gray -- needs a manual DevTools
    #   check, not more automated probing.
    #
    # - Covington & Burling: DROPPED. Real tenant confirmed on Workday wd1 (path-specific-
    #   error signal) but the site slug was never found -- cov.com's business-professionals
    #   page uses Coveo (static.cloud.coveo.com), an enterprise search layer on their
    #   Sitecore CMS, not a job board ATS directly. The #sort=@offices ascending URL
    #   fragment is Coveo's own search-state syntax. Job data is fetched via a JS search API
    #   call after page load, invisible to static HTML scraping. Same category as Ropes &
    #   Gray -- needs a manual DevTools check to find the Coveo API call, not more automated
    #   probing.
}
