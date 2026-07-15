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
    AEMCareerSearchAdapter,
    ApplicantStackAdapter,
    BreezyAdapter,
    CircaWorksAdapter,
    CustomHTMLAdapter,
    DentonsCareerAdapter,
    EArcuAdapter,
    FloRecruitAdapter,
    GreenhouseAdapter,
    JobviteAdapter,
    OracleRecruitingAdapter,
    RadancyAdapter,
    UltiProAdapter,
    VenableAdapter,
    PaulWeissAdapter,
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
    "Proskauer Rose": {
        "adapter": OracleRecruitingAdapter,
        "api_url": (
            "https://dfa.fa.us1.oraclecloud.com/hcmRestApi/resources/latest/"
            "recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
            "&finder=findReqs;siteNumber=CX_1001,limit=100"
        ),
        "job_url_template": (
            "https://dfa.fa.us1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{id}"
        ),
        "notes": "CONFIRMED via live probe -- 38 real requisitions ('Senior Paralegal', "
        "'Business Analyst', 'Help Desk Analyst', 'Billing Specialist'), unmistakably a "
        "real active law-firm ATS. Same Oracle Recruiting Cloud REST pattern already "
        "confirmed for Cozen O'Connor (different host/siteNumber), no adapter changes "
        "needed.",
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
    "Squire Patton Boggs": {
        # New platform for this project: CV-Mail UK (ColdFusion, fsr.cvmailuk.com).
        "adapter": CustomHTMLAdapter,
        "list_url": "https://fsr.cvmailuk.com/spb/main.cfm?page=jobBoard&rcd=1309578"
        "&srxksl=1&groupType_21=5039&filter=",
        "link_selector": "a.jobMoreDetailCaptionStyle",
        "location_selector": "td.col_Job-Location",
        "notes": "CONFIRMED via live probe -- 30 real postings, plausible business-"
        "professional and attorney titles across US offices ('Voice and Unified "
        "Communications Engineer' - Atlanta, 'Litigation Associate' - Cincinnati, "
        "'Financial Services Insurance Associate' - Cleveland). Real per-job detail links "
        "and a dedicated location column (td.col_Job-Location) both confirmed directly in "
        "server-rendered HTML, no JS execution needed. Note: the 'rcd' query param in "
        "job-detail links appears to be a session-scoped tracking ID that changes on every "
        "fetch -- the list_url's own rcd value does not need to stay in sync with it, "
        "confirmed stable across multiple independent live probes.",
    },
    "Sullivan & Cromwell": {
        # New platform for this project: Taleo Business Edition (phg.tbe.taleo.net).
        "adapter": CustomHTMLAdapter,
        "list_url": "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=SULLCROM&cws=38",
        "link_selector": "a.viewJobLink",
        "location_selector": "div[tabindex='0']:last-of-type",
        "notes": "CONFIRMED via live probe -- 10 real postings, plausible business-"
        "professional titles all in New York ('Analyst - Business Development "
        "(Litigation)', 'Assistant, Legal Talent Office - Talent Management', 'Conference "
        "Services Support'). Row markup: <div class=\"oracletaleocwsv2-accordion-head-"
        "info\"> containing <h4><a class=\"viewJobLink\"></a></h4> plus two identical "
        "<div tabindex=\"0\"> siblings, the first empty and the second holding the "
        "location text -- :last-of-type picks the second reliably since both share the "
        "same attributes otherwise. Real per-job URLs (viewRequisition?...&rid=N) "
        "available directly.",
    },
    "Katten Muchin Rosenman": {
        # Same Taleo Business Edition host as Sullivan & Cromwell (phg.tbe.taleo.net), just a
        # different org/cws pair -- identical adapter config shape.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://phg.tbe.taleo.net/phg04/ats/careers/v2/searchResults?org=KATTMUCH2&cws=39",
        "link_selector": "a.viewJobLink",
        "location_selector": "div[tabindex='0']:last-of-type",
        "notes": "CONFIRMED via live probe -- 10 real postings, plausible business-"
        "professional titles ('Applications Engineer' across 6 offices, 'Billing "
        "Coordinator', 'e-Billing Manager'). Same row markup as Sullivan & Cromwell "
        "(oracletaleocwsv2-accordion-head-info wrapping <h4><a class=\"viewJobLink\"></a>"
        "</h4> plus trailing div[tabindex='0'] siblings) -- this tenant's rows show a "
        "department field too (e.g. 'Information Technology'), but :last-of-type still "
        "correctly picks whichever div comes last (location), regardless of how many "
        "siblings precede it.",
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
    "Wilson Sonsini": {
        # WordPress + FacetWP. Generic a[href*='/openings/'] would double-count every posting
        # (a title link AND a separate "Details" link share the identical href) -- the
        # a.link--pointy class uniquely matches only the title link.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://careers.wsgr.com/openings/?_opening_type=82",
        "link_selector": "a.link--pointy",
        "notes": "CONFIRMED via live probe -- real postings include 'Temporary Corporate "
        "Executive Assistant', 'Project Manager', 'Digital Experience/Website Program Lead', "
        "and 'Practice Support Lawyer, M&A' (a genuine KM-adjacent role -- its description "
        "mentions 'building knowledge management infrastructure', though the title itself "
        "doesn't contain an exact AI_KM_KEYWORDS phrase). No location_selector set -- the "
        "office/department/remote-status text sits outside the title link's nearest div "
        "ancestor (CustomHTMLAdapter's row-finding only walks up to the first "
        "tr/li/div match, which stops one level too shallow here), so location comes back "
        "blank for now. Worth revisiting if location text turns out to matter for this firm.",
    },
    "WilmerHale": {
        # SilkRoad OpenHire, new platform for this project. The company's careers page
        # (round 1) was just a search FORM -- fuseaction=app.jobsearch (found via live
        # probing the form's own fuseaction references) returns real results directly on a
        # plain GET, no form submission needed.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://wilmerhale-openhire.silkroad.com/epostings/index.cfm"
        "?fuseaction=app.jobsearch&company_id=16437&version=2",
        "link_selector": "a[href*='fuseaction=app.jobinfo']",
        "notes": "CONFIRMED via live probe -- 54 real postings, plausible business-"
        "professional titles ('Business Development Manager', 'Senior Business Intelligence "
        "Engineer', 'Business Relationship Manager (Law Firm IT Management Consultant)', "
        "'Project Manager'). Repeated titles with different jobid values (e.g. 'Lateral "
        "Recruitment Manager' x3) are genuinely distinct multi-location postings, not a "
        "duplicate-link bug -- same pattern as Fisher Phillips. No location_selector set "
        "yet (not confirmed from static probing); worth revisiting.",
    },
    "Akin Gump": {
        # SilkRoad again (same platform as WilmerHale) but a different URL shape
        # (jobs.silkroad.com/<company>/<company> vs <company>-openhire.silkroad.com/
        # epostings/...), and the WilmerHale fuseaction trick didn't apply. Found via
        # Playwright: the job data is genuinely server-rendered in the raw pre-JS HTML with
        # clean, stable class names -- no Playwright needed at runtime after all.
        "adapter": CustomHTMLAdapter,
        "list_url": "https://jobs.silkroad.com/AkinGump/AkinGump",
        "link_selector": "a.sr-panel",
        "title_selector": ".sr-panel__title",
        "location_selector": ".sr-panel__location .sr-panel__meta",
        "notes": "CONFIRMED via live browser network capture -- real postings include "
        "'Litigation Practice Coordinator' (Washington, DC), 'Public Law & Policy Practice "
        "Manager', 'Billing Assistant', 'Regional IT Support Manager', 'Corporate Practice "
        "Manager'. Real per-job URLs confirmed (/AkinGump/AkinGump/jobs/<id>). KNOWN GAP: "
        "results are paginated ('Page 1 of 2' seen live) and CustomHTMLAdapter has no "
        "pagination support -- this only captures page 1 for now. Worth revisiting if a "
        "simple page= query param turns out to work.",
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
    "Wachtell, Lipton, Rosen & Katz": {
        "adapter": WorkdayAdapter,
        "tenant": "vhr_wachtelllipton",
        "wd": "wd1",
        "site": "wlrk",
        "cxs_host": "wd1.myworkdaysite.com",
        "notes": "CONFIRMED via live probe -- 8 real postings, all New York, unmistakably "
        "law-firm support-staff/IT titles ('Administrative Legal Assistant', 'Word "
        "Processing Lead Operator', 'Systems Analyst', 'ServiceNow Solution Architect'). "
        "Tenant slug 'vhr_wachtelllipton' has an underscore, which is invalid in a real "
        "hostname/wildcard-cert, so the old-style {tenant}.{wd}.myworkdayjobs.com "
        "subdomain SSL-fails (confirmed: CERTIFICATE_VERIFY_FAILED hostname mismatch). "
        "Fix (see cxs_host in WorkdayAdapter): hit the CXS API and build job links "
        "directly off the wd1.myworkdaysite.com domain instead, keeping the tenant slug "
        "in the path rather than as a subdomain. No AI/KM keyword matches in current "
        "postings, but wired in for future coverage.",
    },
    "Skadden Arps": {
        "adapter": WorkdayAdapter,
        "tenant": "skadden",
        "wd": "wd5",
        "site": "Skadden_Careers",
        "notes": "CONFIRMED via live probe -- 77 real postings ('Senior Paralegal', 'Client "
        "Accounting Supervisor', 'Junior Technology Support Analyst', 'Technology Support "
        "Analyst'), unmistakably a real active law-firm ATS. Supersedes an earlier, "
        "incorrect MANUAL_CHECK_FIRMS note that guessed this tenant was 'apparently "
        "dormant/internal' -- the site slug is 'Skadden_Careers', not what that earlier "
        "probe assumed, and it's very much live. Standard old-style Workday subdomain, no "
        "adapter changes needed.",
    },
    "Sidley Austin": {
        "adapter": WorkdayAdapter,
        "tenant": "sidley",
        "wd": "wd501",
        "site": "US",
        "notes": "CONFIRMED via live probe -- 79 real postings ('eBilling Analyst', "
        "'Service Desk Senior Technician', 'Enterprise Architect Senior Director', "
        "'Senior Product Analyst'), unmistakably a real active law-firm ATS. Standard "
        "old-style Workday subdomain, no adapter changes needed.",
    },
    "Munger Tolles": {
        "adapter": WorkdayAdapter,
        "tenant": "mto",
        "wd": "wd503",
        "site": "MTO_Careers",
        "notes": "CONFIRMED via live probe -- 10 real postings, plausible business-"
        "professional titles ('Senior Executive Assistant', 'Legal Systems Administrator - "
        "Talent Systems', 'Senior Manager of Innovation, Systems and Data', 'Billing "
        "Supervisor'). Standard old-style Workday subdomain, no adapter changes needed.",
    },
    "Kramer Levin (now Herbert Smith Freehills Kramer)": {
        # Discovered via Playwright network capture, not static probing -- the visible
        # careers.hsfkramer.com site is Phenom People, but its own embedded search results
        # (phApp.eagerLoadRefineSearch, present directly in the raw pre-JS HTML) revealed
        # each job's real applyUrl pointing at a Workday tenant. Phenom is just a front-end
        # wrapper here; Workday is the actual underlying ATS, and it's directly reachable
        # with zero adapter changes -- no need to fight Phenom's undocumented REST API at
        # all.
        "adapter": WorkdayAdapter,
        "tenant": "herbertsmithfreehills",
        "wd": "wd3",
        "site": "External",
        "notes": "CONFIRMED via live browser network capture -- real postings visible in "
        "Phenom's own embedded search results included 'Help Desk Technician' (New York, "
        "genuine IT/business-professional role) with "
        "applyUrl=https://herbertsmithfreehills.wd3.myworkdayjobs.com/External/job/"
        "New-York/Help-Desk-Technician_R-102884/apply -- confirmed Workday tenant "
        "'herbertsmithfreehills', pod wd3, site 'External'. 12 total postings reported by "
        "Phenom's own search (totalHits:12) at time of discovery. Standard old-style "
        "Workday subdomain, no adapter changes needed despite how it was found.",
    },
    "Hogan Lovells": {
        "adapter": WorkdayAdapter,
        "tenant": "hoganlovells",
        "wd": "wd3",
        "site": "Search",
        "notes": "CONFIRMED via live probe -- 208 real postings, but this is clearly one "
        "global Workday tenant, not US-only (London/Amsterdam/Frankfurt/Hamburg/Hong Kong "
        "dominate the sample) -- same pattern as Clyde & Co US. Rely on keyword/location "
        "filtering downstream rather than URL splitting; most non-US postings simply won't "
        "match the AI/KM keyword list. Standard old-style Workday subdomain, no adapter "
        "changes needed.",
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
    "Baker Hostetler": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting.ultipro.com/BAK1005BKH/JobBoard/"
        "da65e963-280e-4c79-9743-c8622538c0ea/",
        "notes": "CONFIRMED via live probe -- 24 real postings ('Marketing Manager', "
        "'Patent Scientist', 'Paralegal - Corporate / M&A', 'Legal Secretary', 'Practice "
        "Manager', 'Innovation Analyst'), unmistakably a real active law-firm ATS. "
        "Supersedes an earlier MANUAL_CHECK_FIRMS note that only found an empty career "
        "sub-sitemap -- real tenant confirmed directly by the user.",
    },
    "Fox Rothschild": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting.ultipro.com/fox1001frllp/JobBoard/"
        "88a19d60-0e84-49c7-b754-509a756678e7/",
        "notes": "CONFIRMED via live probe -- 23 real postings including a direct target-role "
        "hit ('KM Research Analyst'), plus plausible business-professional titles "
        "('Proposal Manager', 'Office Services Coordinator', 'Senior Business Development "
        "Manager', 'Payment Applications Assistant').",
    },
    "Baker Donelson": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting2.ultipro.com/BAK1000/JobBoard/"
        "2f6b40a8-4e29-e740-a3db-cb1a1e4563b8/",
        "notes": "CONFIRMED via live probe -- 18 real postings, plausible business-"
        "professional titles ('IT Project Manager', 'SharePoint Administrator - Memphis, TN "
        "(Remote)', 'Client Experience & Value Coordinator', 'Practice Coordinator'). Note "
        "the host is recruiting2.ultipro.com (not the more common recruiting.ultipro.com "
        "seen for Akerman/Baker Hostetler/Fox Rothschild) -- UltiProAdapter takes the full "
        "board_url as config so this needed no adapter changes, just preserving the exact "
        "host given.",
    },
    "Hunton Andrews Kurth": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting.ultipro.com/HUN1002HW/JobBoard/"
        "c54d0719-19af-46ae-b27a-8c3695a9ab0a/",
        "notes": "CONFIRMED via live probe -- 23 real postings, plausible business-"
        "professional titles ('CIPL Data Policy Analyst', 'Practice Technology Trainer', "
        "'Legal Project Management Analyst', 'Manager Strategic Communications and "
        "Advocacy').",
    },
    "Eversheds Sutherland": {
        "adapter": UltiProAdapter,
        "board_url": "https://recruiting.ultipro.com/SUT1001EVSU/JobBoard/"
        "80eaa491-46d1-4ef3-93bb-2f523c2631c7/",
        "notes": "CONFIRMED via live probe -- 17 real postings, plausible business-"
        "professional titles ('Content and Brand Manager', 'Senior Manager, Client "
        "Development', 'Public Relations Manager', 'IP Docketing Specialist').",
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
    "Winston Taylor (fka Winston & Strawn)": {
        # Winston & Strawn merged with Taylor Wessing (UK) to form Winston Taylor, effective
        # June 1, 2026 -- outside this project's prior research window, and only surfaced
        # when the user provided the real URL directly. NOT the same tenant as the
        # "winston" HRMdirect collision in REJECTED_LEADS -- that's a real but unrelated
        # food/manufacturing company that happens to share the name; this is a different
        # platform (viGlobal) and a different company entirely.
        "adapter": ViGlobalAdapter,
        "list_url": "https://careers-winstontaylor-americas.viglobalcloud.com/"
        "viRecruitSelfApply/RecDefault.aspx?Tag=ebd45de2-7676-4bca-b282-f92bfe9d5968",
        "notes": "CONFIRMED via user-provided sample (not this project's own live probe, "
        "sandbox has no outbound network access) -- real postings visible include direct "
        "target-role hits ('Charlotte - AI Adoption Specialist', 'Chicago - AI Adoption "
        "Specialist', 'Charlotte - Practice Innovation Product Specialist', 'Charlotte - "
        "Practice Innovation Workflow Coordinator', 'Chicago - Attorney Integration "
        "Coordinator') plus business-development titles, across offices consistent with "
        "Winston & Strawn's real footprint (Chicago is its historic HQ). Row template shape "
        "(concatenated-text-blob vs. structured <h4>/<h5> tags, see viglobal.py) not yet "
        "confirmed -- ViGlobalAdapter tries both automatically, but this hasn't been "
        "verified against a real live scrape yet. Recommend running the scraper for real "
        "and checking debug_all_titles.txt before fully trusting this entry.",
    },
    "Vinson & Elkins": {
        # Third viGlobal row-template shape found in this project, hosted on the firm's own
        # domain (portal.velaw.com) rather than viglobalcloud.com -- see viglobal.py's module
        # docstring. Table id is also non-default ("contentPlaceHolder_dataGridMain", not the
        # usual "contentPlaceHolder_gridviewList").
        "adapter": ViGlobalAdapter,
        "list_url": "https://portal.velaw.com/viDesktopEx/viRecruitSelfApply/ReDefault.aspx"
        "?FilterREID=7",
        "table_id": "contentPlaceHolder_dataGridMain",
        "notes": "CONFIRMED via live probe -- real postings include 'Billing Coordinator', "
        "'Event and Travel Logistics Specialist', 'Head of Risk & Compliance, "
        "International', 'Human Resources Manager', 'International Business Development "
        "Manager'. Unlike the other two viGlobal tenants, this template's 'More Info' "
        "control is a real <a href> link (ReJobView.aspx?...&JobID=N), not a "
        "javascript:__doPostBack(...) postback -- ViGlobalAdapter now picks up real "
        "per-job URLs and posting IDs when that's available (see viglobal.py), so this "
        "firm gets accurate deep links unlike O'Melveny/Bryan Cave. FIXED (via Playwright "
        "investigation) the intermittent zero-postings bug seen on scheduled runs: the "
        "original list_url used a ?Tag=<GUID> parameter that turned out to be a "
        "session-scoped/expiring link -- loading it in a fresh browser redirected straight "
        "to the plain velaw.com homepage instead of the job board. The real careers page's "
        "'Explore Current Opportunities' link uses a stable ?FilterREID=7 parameter instead, "
        "which doesn't expire -- switched to that.",
    },
    "Bracewell": {
        "adapter": ViGlobalAdapter,
        "list_url": "https://bracewellselfapply.viglobalcloud.com/viRecruitSelfApply/"
        "RecDefault.aspx?Tag=a9725fb0-5ae5-4b9f-accd-4441e0d4ec4e",
        "notes": "CONFIRMED via live probe -- real postings include 'Billing Rates Analyst', "
        "'Business Applications Administrator', 'Marketing Applications Manager', 'PRG "
        "Executive Coordinator', 'Strategic Communications Specialist'. Bryan Cave-style "
        "structured <h4>/<h5> row shape confirmed directly (default table_id, no override "
        "needed). Supersedes an earlier MANUAL_CHECK_FIRMS note that only found an empty "
        "career sub-sitemap -- real tenant confirmed directly by the user.",
    },
    "Jones Day": {
        "adapter": ViGlobalAdapter,
        "list_url": "https://jonesdaystaffrecruitselfapply.viglobalcloud.com/"
        "viRecruitSelfApply/RecDefault.aspx?Tag=ab6501e1-c8b5-402c-8909-e3e6af6d4e73",
        "notes": "CONFIRMED via live probe -- default gridviewList table present with a real "
        "549KB response, but no <h4> tags found (unlike Bracewell/Bryan Cave/Vinson & "
        "Elkins), so this is presumably O'Melveny's concatenated-text-blob row shape rather "
        "than the structured one -- ViGlobalAdapter tries both automatically, but the "
        "text-blob regex match itself hasn't been verified against this tenant's exact "
        "output yet. Recommend checking debug_all_titles.txt after a real run before fully "
        "trusting this entry.",
    },
    "Mintz Levin": {
        "adapter": ViGlobalAdapter,
        "list_url": "https://careers.mintz.com/viRecruitSelfApply/RecDefault.aspx"
        "?Tag=fdfa0684-8265-4911-aece-f31f96213ea9",
        "notes": "CONFIRMED via live probe -- real postings include 'Business Development "
        "Coordinator', 'Business Development Manager, Litigation', 'Conflicts Analyst', "
        "'External Communications Specialist', 'Financial Planning Analyst'. Bryan Cave-"
        "style structured <h4> row shape confirmed directly (default table_id, no override "
        "needed), hosted on the firm's own domain (careers.mintz.com) rather than "
        "viglobalcloud.com, same as Winston Taylor and Vinson & Elkins.",
    },
    "Duane Morris": {
        # Found via its marketing page's "Support Staff Opportunities" accordion, whose
        # per-city links (selfapply.duanemorris.com/viselfapply/viRecruitSelfApply/
        # RecDefault.aspx?FilterREID=2&FilterJobCategoryID=22&FilterJobID=N) are the same
        # viRecruitSelfApply platform as O'Melveny/Bryan Cave/Vinson & Elkins/Bracewell/
        # Mintz -- no Playwright or new adapter code needed, just this config entry.
        "adapter": ViGlobalAdapter,
        "list_url": "https://selfapply.duanemorris.com/viselfapply/viRecruitSelfApply/"
        "RecDefault.aspx?FilterREID=2",
        "notes": "CONFIRMED via plain zero-JS HTTP request (not just browser-rendered) -- "
        "the FilterREID=2 param matches the one embedded in every real per-job href found "
        "on the marketing page's Support Staff accordion, and the response's first real "
        "row is 'Accounts Payable Clerk - Philadelphia', a genuine staff posting (not an "
        "attorney role) confirming the filter targets the right bucket. Bryan Cave-style "
        "structured <h4>/<h5> row shape confirmed directly (default table_id, no override "
        "needed) -- unlike Bryan Cave's tenant, this one's description div is populated "
        "server-side too, but ViGlobalAdapter's structured-row parser doesn't currently "
        "read it (hardcoded empty), same as every other structured-shape tenant -- a "
        "possible future enhancement, not required for this firm to work.",
    },
    # --- Breezy HR group ---------------------------------------------------
    "Marshall Dennehey": {
        "adapter": BreezyAdapter,
        "json_url": "https://marshall-dennehey.breezy.hr/json",
        "notes": "CONFIRMED via live probe -- 89 real postings, clean public JSON API "
        "(https://<subdomain>.breezy.hr/json, no auth/pagination needed). New platform for "
        "this project (Breezy HR). Every current posting is attorney-track or explicitly "
        "hard-excluded support staff (Paralegal, Legal Secretary) EXCEPT a handful of "
        "genuine business-professional/IT-adjacent roles ('Cyber Security Engineer', "
        "'Litigation Support Specialist', 'Project Assistant') that don't happen to hit any "
        "current AI_KM_KEYWORDS term -- same situation as Wachtell Lipton, wired in for "
        "future coverage rather than dropped, since real non-attorney roles do exist here "
        "(unlike Weil Gotshal, which was confirmed 100% attorney-only).",
    },
    # --- Radancy group ---------------------------------------------------
    "Ogletree Deakins": {
        # New platform for this project (tentatively identified as Radancy "Attract" from a
        # "ccc.attract.portal.url" key in the response's own metadata, not independently
        # confirmed). Underlying ATS is actually iCIMS per each job's own ats_code field, but
        # this wrapper endpoint isn't behind the WAF block that blocks iCIMS everywhere else
        # in this project -- a clean path to the same data.
        "adapter": RadancyAdapter,
        "api_url": "https://careers.ogletree.com/api/jobs",
        "notes": "CONFIRMED via live probe (5 diagnostic rounds) -- 148 real postings across "
        "15 pages, sample titles plausibly genuine ('Senior Financial Systems Analyst', "
        "'Sr. Cloud Administrator', 'Litigation Paralegal'). Pagination is page-number-based "
        "(?page=N, 1-indexed) -- start/offset/num params are all silently ignored, and the "
        "server hard-caps each page to 10 regardless of what's requested. Verified end-to-"
        "end: page=15 returns the trailing 8 jobs (140+8=148), page=16 returns empty. Full "
        "job description text (qualifications + responsibilities) is present in the list "
        "response at no extra request cost, folded into description the same way Oracle "
        "Recruiting Cloud's adapter does. meta_data.canonical_url preferred over apply_url "
        "for the stored link (apply_url redirects straight into an iCIMS login flow).",
    },
    # --- AEM Career Search group ---------------------------------------------------
    "Dechert": {
        # Bespoke AEM (Adobe Experience Manager) career-search feature, not a third-party
        # ATS -- found by digging into the page's embedded Sling servlet config
        # (careerSearchPath/type/positionsOpt) after 3 rounds of static-HTML dead ends.
        "adapter": AEMCareerSearchAdapter,
        "api_url": "https://www.dechert.com/bin/careersSearch",
        "notes": "CONFIRMED via live probe (4 diagnostic rounds) -- 84 real postings in one "
        "response, no pagination (Total=84 matches the returned array length exactly). "
        "Sample titles include 'Manager, Client Events' (Marketing) and a real Type field "
        "per posting ('Business Professional' vs 'Experienced Lawyer' etc.) -- not used for "
        "pre-filtering since title/keyword filtering downstream already does the real work, "
        "but confirms real non-attorney postings exist. Each posting's Url actually points "
        "at dechertselfapply.viglobalcloud.com (the underlying data is proxied from a real "
        "viGlobal backend), but this AEM wrapper endpoint has no bot protection unlike "
        "hitting that backend directly.",
    },
    # --- FloRecruit group ---------------------------------------------------
    "Sheppard Mullin": {
        # First real win from the Playwright network-capture investigation (see
        # diagnose_browser.py) -- previously blocked because the visible page only calls a
        # GraphQL endpoint with an undiscoverable query shape, but a plain public REST
        # endpoint returns everything directly with no auth/session needed at all.
        "adapter": FloRecruitAdapter,
        "api_url": "https://florecruit.com/api/v2/public-jobs/sheppardbusinessservices/"
        "career-page-jobs",
        "list_url": "https://florecruit.com/v2/app/sheppardbusinessservices/jobs",
        "notes": "CONFIRMED via live browser network capture -- 16 real postings in one "
        "response, no pagination needed. Sample titles unmistakably genuine ('IP Docketing "
        "Specialist', 'Trademark Paralegal', 'eDiscovery Project Manager', 'Technology "
        "Services Administrator'). Confirmed the endpoint works from a completely fresh, "
        "unauthenticated request (not just from within an established browser session), so "
        "no Playwright needed at runtime despite how it was discovered. No confirmed "
        "per-job URL pattern yet -- falls back to list_url.",
    },
    # --- Dentons Career Search group ---------------------------------------------------
    "Dentons": {
        "adapter": DentonsCareerAdapter,
        "api_url": "https://www.dentons.com/DentonsServices/career.asmx/GetJobsByState",
        "context_item": "{4CCB9477-3A1B-4C92-8FB9-6282C913B18D}",
        "context_url": "https://www.dentons.com/en/careers/careers-in-the-united-states/"
        "business-services-in-the-united-states/",
        "notes": "CONFIRMED via live browser network capture -- a bespoke ASP.NET .asmx "
        "web service (career.asmx/GetJobsByState), not a 3rd-party ATS. Real postings with "
        "genuine per-job URLs ('E-Billing Coordinator', 'Lateral Conflicts Analyst', 'Legal "
        "Administrative Assistant (Intellectual Property & Technology) - New York'). All "
        "context needed is carried directly in the query string (contextItem/"
        "contextItemUrl/contextSite) rather than session cookies, so this should work via a "
        "plain request without a prior page visit -- confirmed the endpoint itself returns "
        "real data this way, though the exact contextItem GUID was sourced from a live "
        "browser session rather than independently derived. No location field in the "
        "response; narrative (real description HTML) folded into description instead.",
    },
    # --- Playwright (runtime browser) group ---------------------------------------------------
    "Venable": {
        # First genuine runtime PlaywrightAdapter use in this project -- every other firm
        # found via the Playwright investigation turned out to have a plain HTTP-reachable
        # API or static HTML underneath once discovered. Venable's ADP myjobs site renders
        # job cards as Angular web components (<sdf-button>) with no plain <a href> at all,
        # and the real underlying REST API 400s on every replay attempt tried (fresh
        # context, established session) -- reading the rendered DOM directly is the only
        # path found after 4 diagnostic rounds.
        "adapter": VenableAdapter,
        "list_url": "https://myjobs.adp.com/venablebusinessprofessionalcareers/cx",
        "notes": "CONFIRMED via live browser network capture -- real postings include "
        "'Conflicts Attorney' (Los Angeles). Title comes from an sdf-button's aria-label "
        "attribute, location from a .reqLocation span, both nested in div.job-details. No "
        "real per-job URL exists in the DOM (JS-only interactive buttons) -- posting_id is "
        "a title+location hash and url falls back to list_url, same pattern as viGlobal's "
        "postback-only tenants. UNCONFIRMED: the API reported 26 total postings during "
        "discovery but only a handful render without interaction -- this scrolls the page "
        "a few times first on the assumption jobs lazy-load, but that specific behavior "
        "wasn't independently verified. Check debug_all_titles.txt after a real run to "
        "confirm the full count comes through.",
    },
    "Paul Weiss": {
        # Second genuine runtime PlaywrightAdapter use -- classic Taleo Enterprise search
        # only populates results after a self-submitting POST triggered by clicking Search,
        # with no discoverable AJAX/REST endpoint after several diagnostic rounds.
        "adapter": PaulWeissAdapter,
        "list_url": "https://paulweiss.taleo.net/careersection/ex/jobsearch.ftl",
        "notes": "CONFIRMED via live browser -- 11 real postings including 'Business "
        "Services Assistant', 'Conflicts Analyst', 'Docketing Clerk'. Title + requisition "
        "ID + work location come from each row's rendered text (no real per-job href in "
        "the listing itself, postback-only JS), but classic Taleo Enterprise serves a "
        "real, plain GET-able detail page at jobdetail.ftl?job=<requisitionID> -- "
        "confirmed live for requisition 26000223 -- used as the per-posting URL/ID "
        "instead of falling back to the list page.",
    },
    "Crowell & Moring": {
        # Confirmed via live browser network capture to be plain Greenhouse underneath a
        # custom embed UI -- same adapter as Wilson Elser/Gibson Dunn, no new code needed.
        "adapter": GreenhouseAdapter,
        "board_token": "crowellmoring",
        "notes": "CONFIRMED via live probe -- the careers page embeds "
        "job-boards.greenhouse.io (for=crowellmoring) through the newer embed UI, but the "
        "classic public boards-api.greenhouse.io/v1/boards/crowellmoring/jobs endpoint "
        "this project's GreenhouseAdapter already calls works too: 17 real postings "
        "including 'Business Development Coordinator', 'Collections Specialist', "
        "'eDiscovery & Data Solutions Technical Analyst'.",
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
    # =========================================================================
    # CONFIRMED genuine technical obstacle (WAF/bot-protection, credential-gated
    # API, or JS-rendered page with a confirmed real ATS/tenant underneath) --
    # real postings likely exist behind each of these, worth a human checking
    # manually. This tier intentionally runs well past the "5-10 firms" target
    # discussed when this list was last restructured -- every entry here has an
    # actual confirmed block, not just "we couldn't find it," so none were cut
    # just to hit a smaller number.
    # =========================================================================
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
    "Lewis Brisbois": {
        # Previously dropped entirely from config.py per explicit request (both this firm
        # and Gordon Rees were confirmed iCIMS tenants blocked by the same WAF challenge as
        # Orrick/Milbank, with no automatable path). Re-added here as a manual-check entry
        # so it's visible on the dashboard rather than invisible -- it was never scrapable,
        # dropping it from FIRMS was correct, but that shouldn't mean losing track of it.
        "reason": "Confirmed iCIMS tenant 'lewisbrisbois', blocked by the same AWS WAF "
        "'Human Verification' challenge as Orrick/Milbank -- not scrapable with a plain "
        "HTTP client.",
        "tenant": "lewisbrisbois",
        "search_url": "https://careers-lewisbrisbois.icims.com/jobs/search",
        "check_url": "https://www.lewisbrisbois.com/careers",
    },
    "Gordon Rees": {
        "reason": "Confirmed iCIMS tenant 'grsm' (Gordon Rees Scully Mansukhani), blocked "
        "by the same AWS WAF 'Human Verification' challenge as Orrick/Milbank -- not "
        "scrapable with a plain HTTP client.",
        "tenant": "grsm",
        "search_url": "https://careers-grsm.icims.com/jobs/search",
        "check_url": "https://www.grsm.com/careers",
    },
    "Milbank": {
        "reason": "Real ATS is iCIMS (found via the firm's own careers page), blocked by the "
        "same AWS WAF 'Human Verification' challenge as Orrick. A Workday tenant also exists "
        "on wd1 but is apparently dormant/internal, not used for external recruiting.",
        "tenant": "milbank",
        "search_url": "https://careers-milbank.icims.com/jobs/intro?hashed=-435594439",
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
    "Willkie Farr & Gallagher": {
        # Upgraded from "no ATS platform domain present" -- that scan only checked
        # willkie.com/careers's static HTML, which apparently doesn't embed this link
        # server-side. Real tenant confirmed directly by the user.
        "reason": "Confirmed iCIMS tenant 'jobs-willkie' (note: jobs- subdomain prefix, not "
        "the more common careers- prefix seen for Orrick/Milbank/Nelson Mullins/Foley & "
        "Lardner), blocked by the same AWS WAF 'Human Verification' challenge -- not "
        "scrapable with a plain HTTP client.",
        "tenant": "jobs-willkie",
        "search_url": "https://jobs-willkie.icims.com/jobs/search?hashed=-625885970",
        "check_url": "https://www.willkie.com/careers",
    },
    "McDermott Will & Emery": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. mwe.com/careers redirects to mcdermottlaw.com/careers, "
        "which is blocked by an Imperva Incapsula bot-protection challenge -- not scrapable "
        "with a plain HTTP client, same category as iCIMS's AWS WAF block.",
        "check_url": "https://www.mcdermottlaw.com/careers",
    },
    "Covington & Burling": {
        "reason": "Real tenant confirmed on Workday wd1 (path-specific-error signal) but the "
        "site slug was never found -- the business-professionals page uses Coveo "
        "(static.cloud.coveo.com), an enterprise search layer on their Sitecore CMS, not a "
        "job board ATS directly. Job data is fetched via a JS search API call after page "
        "load, invisible to static HTML scraping.",
        "check_url": "https://www.cov.com/en/careers/business-professionals/employment-opportunities",
    },
    "Arnold & Porter": {
        "reason": "Confirmed Coveo (static.cloud.coveo.com), the exact same enterprise "
        "search layer already blocking Covington & Burling -- job data is fetched via a JS "
        "search API call after page load. Checked specifically for an embedded "
        "organizationId/accessToken in the static HTML (Coveo sites sometimes expose these "
        "for a public search widget) and found neither -- genuinely invisible to static "
        "HTML scraping, not just unconfirmed.",
        "check_url": "https://www.arnoldporter.com/en/careers/professional-staff/"
        "current-opportunities",
    },
    "Davis Polk": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. The real careers path wasn't found -- "
        "davispolk.com/careers returns 403 (bot-protected) and the bare domain has no ATS "
        "trace.",
        "check_url": "https://www.davispolk.com",
    },
    "Ropes & Gray": {
        # CONFIRMED via genuine headless-Chromium Playwright, not just plain requests --
        # ropesgrayrecruiting.com's own "US Careers" click-through returns a real
        # Cloudflare "Attention Required!" interstitial ("Sorry, you have been blocked" /
        # security-service block page) to a real browser session, not just a bare HTTP
        # client. Same category of obstacle as Kirkland & Ellis's Cloudflare block --
        # genuinely not scrapable, not just JS-rendering-blocked.
        "reason": "Confirmed Cloudflare bot-management block (real 'Attention Required!' "
        "challenge page, not just a 403) on ropesgrayrecruiting.com's US Careers page, "
        "verified with a real headless-Chromium browser session -- not scrapable even "
        "with Playwright. A real ApplicantStack tenant may exist "
        "(ropesgray.applicantstack.com/x/openings returned 0 postings), but that's not "
        "enough to confirm identity.",
        "check_url": "https://ropesgray.applicantstack.com/x/openings",
    },
    "Cleary Gottlieb": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. clearygottlieb.com/careers redirects to the bare "
        "homepage (Sitefinity CMS) -- the real careers subpage URL wasn't found.",
        "check_url": "https://www.clearygottlieb.com/careers",
    },
    "Morrison & Foerster": {
        "reason": "Real tenant confirmed on Workday wd5 (path-specific-error signal), "
        "apparently dormant/internal. mofo.com/careers redirects to careers.mofo.com, a "
        "Next.js SPA with zero job data in static HTML -- the real ATS/API wasn't identified.",
        "check_url": "https://careers.mofo.com/",
    },
    "K&L Gates": {
        "reason": "Real 'All Current Openings' link found, leading to klgates.recsolu.com -- "
        "RecSolu (Yello Enterprise), a platform not otherwise seen in this project. The board "
        "is JS-rendered with no job data in static HTML; several guessed REST API endpoints "
        "(/api/v1/job_boards/.../jobs) returned 401 Unauthorized -- a real API exists but "
        "requires credentials this project doesn't have and shouldn't try to bypass.",
        "check_url": "https://klgates.recsolu.com/job_boards/1",
    },
    "Latham & Watkins": {
        "reason": "Confirmed iCIMS tenant 'lw' (careers-lw.icims.com), blocked by the same "
        "AWS WAF 'Human Verification' challenge as Orrick/Milbank -- not scrapable with a "
        "plain HTTP client.",
        "tenant": "lw",
        "search_url": "https://careers-lw.icims.com/jobs/search?hashed=-625915638",
        "check_url": "https://www.lw.com",
    },
    "Mayer Brown": {
        "reason": "Confirmed iCIMS tenant 'mayerbrown' (note: globalcareers- subdomain "
        "prefix, a third variant after careers-/jobs- seen for other firms), blocked by "
        "the same AWS WAF 'Human Verification' challenge -- not scrapable with a plain "
        "HTTP client.",
        "tenant": "mayerbrown",
        "search_url": "https://globalcareers-mayerbrown.icims.com/jobs/search?hashed=124489139",
        "check_url": "https://www.mayerbrown.com",
    },
    "Kirkland & Ellis": {
        "reason": "Real careers site confirmed (staffjobsus.kirkland.com/jobs/search/), but "
        "blocked by a Cloudflare bot-management challenge ('Just a moment...' interstitial, "
        "confirmed via response body/CSP headers) -- a different bot-protection vendor than "
        "the AWS WAF/Imperva blocks seen elsewhere in this project, but the same category of "
        "obstacle. Underlying ATS platform not identified (blocked before any platform "
        "signal was visible).",
        "check_url": "https://staffjobsus.kirkland.com/jobs/search/",
    },
    "Blank Rome": {
        # Explicit decision, not a technical dead end -- user confirmed live that the
        # business-professionals page has real per-position hyperlinks, but every one leads
        # to an email-based apply form rather than any scrapable ATS/listing API. Nothing
        # left for an adapter to hook into; staying manual permanently per explicit request.
        "reason": "CONFIRMED (user's own live check): the business-professionals careers "
        "page has real per-position hyperlinks, but each leads to an email-based apply "
        "form, not a third-party ATS or any scrapable listing API. No fetchable job data "
        "exists to build an adapter against -- staying manual by explicit decision, not "
        "because of a technical block.",
        "check_url": "https://www.blankrome.com/careers/overview/business-professionals/",
    },
    # =========================================================================
    # UNRESEARCHED -- no confirmed technical block AND no confirmed real/absent
    # postings, just "couldn't find an ATS via sitemap search." Not proven blocked,
    # not proven empty -- needs an actual fresh look (visit the site, check for
    # listings) before it can be classified into the tier above or dropped
    # entirely.
    # =========================================================================
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
    "an unrelated food/manufacturing company that happens to also be named Winston Taylor "
    "(winstontaylor.com) -- a naming coincidence with FIRMS['Winston Taylor (fka Winston & "
    "Strawn)'], NOT the same company. That entry is the real merged law firm (Winston & "
    "Strawn + Taylor Wessing, June 2026), confirmed on a completely different platform "
    "(viGlobal) with real legal-industry job titles. Two unrelated real companies "
    "coincidentally share this name; don't conflate them.",
    "goodwin (Greenhouse board_token)": "Guessed for Goodwin Procter -- confirmed collision, "
    "same shape as Winston & Strawn's. Goodwin Procter's real ATS is Workday (see "
    "FIRMS['Goodwin Procter']); this Greenhouse tenant with its 1 thin, non-legal posting "
    "belongs to some other company.",
}
