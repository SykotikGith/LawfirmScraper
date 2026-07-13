"""AmLaw 100 batch, round 4: fixes two bugs from round 3's sitemap sweep
and deep-inspects every real careers URL found so far.

Bug 1: CAREER_KEYWORD_RE matched "career" as a bare substring anywhere,
catching marketing/publications slugs that merely mention the word (e.g.
Sidley's "...a-second-shot-at-a-legal-career" or Dechert's unrelated "UK
Job Support Scheme" legal alert) instead of requiring it to be an actual
path segment. Fixed to require a leading "/" before "career(s)" or
"job(s)/".

Bug 2: when a sitemap's own <loc> entries include a NAMED sub-sitemap
file (e.g. Bracewell's poa_career-sitemap.xml, Baker Hostetler's
bakerlaw.com/poa_career-sitemap.xml), the old code's substring check
happened to match "career" against the sub-sitemap's own filename and
returned it as if it were a real page -- it was never fetched and
drilled into. Fixed: any candidate ending in .xml is now always treated
as a sitemap and expanded one level before being scanned as a page.

Two groups processed:
  A) Firms with an already-confirmed real careers URL from round 3
     (Vinson & Elkins, Baker Donelson, Ogletree Deakins, Fox Rothschild,
     Willkie Farr, Baker Botts, Dechert, Dentons, Sheppard Mullin -- note
     Sheppard Mullin's real domain is sheppard.com, not sheppardmullin.com
     as guessed) -- deep-fetched directly: scanned for known ATS domains,
     checked for SPA framework markers, and scanned for secondary links
     whose text suggests "view openings"/"search jobs" (the real ATS is
     often one click deeper than the marketing landing page).
  B) Every other firm (sub-sitemap-stuck + zero-hit + noise-only from
     round 3) -- re-run sitemap discovery with the fixed regex, plus a
     robots.txt fallback to find the sitemap location if the guessed
     paths didn't have one.

Usage: python -m scraper.diagnose
Writes diagnose_results.md alongside printing progress to stderr and the
final table to stdout.
"""
from __future__ import annotations

import concurrent.futures
import re
import sys

import requests
from bs4 import BeautifulSoup

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15
MAX_WORKERS = 10
SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]

# Require an actual path-segment boundary, not a bare substring.
CAREER_PATH_RE = re.compile(r"/careers?(?:[/\-]|$)", re.IGNORECASE)
JOB_PATH_RE = re.compile(r"/jobs?/", re.IGNORECASE)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)

ATS_DOMAIN_PATTERNS = {
    "iCIMS": r"icims\.com",
    "Greenhouse": r"greenhouse\.io",
    "Oracle Recruiting Cloud": r"oraclecloud\.com",
    "ApplicantStack": r"applicantstack\.com",
    "HRMdirect": r"hrmdirect\.com",
    "viGlobal": r"viglobalcloud\.com",
    "Circa Works": r"circaworks\.com",
    "PageUp/eArcu": r"\bearcu\b",
    "UltiPro": r"ultipro\.com",
    "Jobvite": r"jobvite\.com",
    "Phenom": r"phenompeople\.com",
    "SmartRecruiters": r"smartrecruiters\.com",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors\.com",
    "Avature": r"avature\.net",
    "Lever": r"jobs\.lever\.co",
    "BambooHR": r"bamboohr\.com",
    "Workday (any format)": r"myworkday(?:jobs|site)\.com",
}

FRAMEWORK_MARKERS = {
    "Angular": r'ng-app="',
    "Next.js": r"_next/static",
    "React (generic)": r"data-reactroot",
    "Vue": r"data-v-app",
}

SECONDARY_LINK_HINTS = re.compile(
    r"view\s*opening|search\s*job|open\s*position|current\s*opening|apply\s*now|job\s*search|job\s*board",
    re.IGNORECASE,
)

# (firm, known-real careers URL) -- group A
KNOWN_CAREER_URLS: list[tuple[str, str]] = [
    ("Vinson & Elkins", "https://www.velaw.com/careers/business-professionals/"),
    ("Baker Donelson", "https://www.bakerdonelson.com/careers"),
    ("Ogletree Deakins", "https://ogletree.com/about-us/careers/"),
    ("Fox Rothschild", "https://www.foxrothschild.com/careers-for-attorneys/open-positions"),
    ("Willkie Farr & Gallagher", "https://www.willkie.com/careers"),
    ("Baker Botts", "https://www.bakerbotts.com/careers/careers-at-baker-botts"),
    ("Dechert", "https://www.dechert.com/careers/law-students.html"),
    ("Dentons", "https://www.dentons.com/en/careers/careers-in-the-united-states/business-services-in-the-united-states/"),
    ("Sheppard Mullin", "https://www.sheppard.com/careers"),
]

# (firm, domain guess) -- group B: everyone else from the 37
GROUP_B_FIRMS: list[tuple[str, str]] = [
    ("Kirkland & Ellis", "www.kirkland.com"),
    ("Latham & Watkins", "www.lw.com"),
    ("Sidley Austin", "www.sidley.com"),
    ("Wachtell Lipton", "www.wlrk.com"),
    ("Quinn Emanuel", "www.quinnemanuel.com"),
    ("Paul Weiss", "www.paulweiss.com"),
    ("Jones Day", "www.jonesday.com"),
    ("Sullivan & Cromwell", "www.sullcrom.com"),
    ("Wilson Sonsini", "www.wsgr.com"),
    ("WilmerHale", "www.wilmerhale.com"),
    ("K&L Gates", "www.klgates.com"),
    ("Squire Patton Boggs", "www.squirepattonboggs.com"),
    ("Mayer Brown", "www.mayerbrown.com"),
    ("Duane Morris", "www.duanemorris.com"),
    ("Proskauer Rose", "www.proskauer.com"),
    ("Kramer Levin", "www.kramerlevin.com"),
    ("Arnold & Porter", "www.arnoldporter.com"),
    ("Crowell & Moring", "www.crowell.com"),
    ("Hunton Andrews Kurth", "www.huntonak.com"),
    ("Venable", "www.venable.com"),
    ("Munger Tolles", "www.mto.com"),
    ("Bracewell", "www.bracewell.com"),
    ("Eversheds Sutherland", "www.eversheds-sutherland.com"),
    ("Akin Gump", "www.akingump.com"),
    ("Baker Hostetler", "www.bakerlaw.com"),
    ("Katten Muchin Rosenman", "www.katten.com"),
    ("Mintz Levin", "www.mintz.com"),
    ("Winston & Strawn", "www.winston.com"),
]


def fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.text


def looks_like_sitemap(url: str) -> bool:
    return url.lower().split("?")[0].endswith(".xml")


def is_real_career_or_job_page(url: str) -> bool:
    return bool(CAREER_PATH_RE.search(url) or JOB_PATH_RE.search(url))


def find_real_pages_in_sitemap(text: str, depth: int = 0) -> list[str]:
    locs = LOC_RE.findall(text)
    real_pages = [loc for loc in locs if not looks_like_sitemap(loc) and is_real_career_or_job_page(loc)]
    if real_pages or depth >= 1:
        return real_pages[:5]

    sub_sitemaps = [loc for loc in locs if looks_like_sitemap(loc) and CAREER_PATH_RE.search(loc.replace("-sitemap", "/careers"))]
    for sub in sub_sitemaps[:3]:
        sub_text = fetch(sub)
        if sub_text is None:
            continue
        found = find_real_pages_in_sitemap(sub_text, depth=depth + 1)
        if found:
            return found
    return []


def find_via_robots(domain: str) -> list[str]:
    text = fetch(f"https://{domain}/robots.txt")
    if text is None:
        return []
    sitemap_lines = re.findall(r"(?im)^Sitemap:\s*(\S+)", text)
    return sitemap_lines[:3]


def discover_career_pages(domain: str) -> tuple[list[str], list[str]]:
    """Returns (real_pages, sitemap_urls_tried)."""
    tried = []
    for path in SITEMAP_PATHS:
        url = f"https://{domain}{path}"
        tried.append(url)
        text = fetch(url)
        if text is None:
            continue
        pages = find_real_pages_in_sitemap(text)
        if pages:
            return pages, tried

    for sm_url in find_via_robots(domain):
        tried.append(sm_url)
        text = fetch(sm_url)
        if text is None:
            continue
        pages = find_real_pages_in_sitemap(text)
        if pages:
            return pages, tried

    return [], tried


def deep_inspect(url: str) -> dict:
    text = fetch(url)
    if text is None:
        return {"url": url, "status": "FETCH FAILED", "ats": None, "frameworks": [], "secondary_links": []}

    ats_hit = None
    for label, pattern in ATS_DOMAIN_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            ats_hit = label
            break

    frameworks = [label for label, pattern in FRAMEWORK_MARKERS.items() if re.search(pattern, text, re.IGNORECASE)]

    soup = BeautifulSoup(text, "lxml")
    secondary = []
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        if link_text and SECONDARY_LINK_HINTS.search(link_text):
            secondary.append((link_text, a["href"]))

    return {"url": url, "status": "OK", "ats": ats_hit, "frameworks": frameworks, "secondary_links": secondary[:5]}


def process_group_a(firm: str, url: str) -> dict:
    result = deep_inspect(url)
    return {"firm": firm, "group": "A", "career_urls": [url], **result}


def process_group_b(firm: str, domain: str) -> dict:
    pages, tried = discover_career_pages(domain)
    if not pages:
        return {"firm": firm, "group": "B", "career_urls": [], "sitemap_tried": tried,
                "url": None, "status": "no real career/job pages found", "ats": None,
                "frameworks": [], "secondary_links": []}
    result = deep_inspect(pages[0])
    result["sitemap_tried"] = tried
    return {"firm": firm, "group": "B", "career_urls": pages, **result}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {}
        for firm, url in KNOWN_CAREER_URLS:
            futures[pool.submit(process_group_a, firm, url)] = firm
        for firm, domain in GROUP_B_FIRMS:
            futures[pool.submit(process_group_b, firm, domain)] = firm

        done = 0
        total = len(KNOWN_CAREER_URLS) + len(GROUP_B_FIRMS)
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            summary = result.get("ats") or result.get("status") or "?"
            print(f"[{done}/{total}] {result['firm']} ({result['group']}): {summary}"
                  f"{' -- ' + result['url'] if result.get('url') else ''}", file=sys.stderr)

    order = {firm: i for i, firm in enumerate([f for f, _ in KNOWN_CAREER_URLS] + [f for f, _ in GROUP_B_FIRMS])}
    results.sort(key=lambda r: order[r["firm"]])

    lines = ["| Firm | Group | URL checked | ATS found | Frameworks | Secondary links |", "|---|---|---|---|---|---|"]
    for r in results:
        sec = "; ".join(f"{t} ({h})" for t, h in r.get("secondary_links", [])) or "-"
        lines.append(
            f"| {r['firm']} | {r['group']} | {r.get('url') or '-'} | {r.get('ats') or r.get('status')} | "
            f"{', '.join(r.get('frameworks', [])) or '-'} | {sec} |"
        )
    table = "\n".join(lines)
    print("\n" + table)

    with open("diagnose_results.md", "w", encoding="utf-8") as f:
        f.write(table + "\n\n")
        for r in results:
            f.write(f"## {r['firm']} (group {r['group']})\n")
            f.write(f"URL checked: {r.get('url')}\n")
            f.write(f"Status/ATS: {r.get('ats') or r.get('status')}\n")
            if r.get("frameworks"):
                f.write(f"Frameworks: {r['frameworks']}\n")
            if r.get("secondary_links"):
                f.write("Secondary links:\n")
                for t, h in r["secondary_links"]:
                    f.write(f"- {t!r} -> {h}\n")
            if r.get("career_urls"):
                f.write(f"All career URLs found: {r['career_urls']}\n")
            if r.get("sitemap_tried"):
                f.write(f"Sitemaps tried: {r['sitemap_tried']}\n")
            f.write("\n")
    print("\nWritten to diagnose_results.md", file=sys.stderr)


if __name__ == "__main__":
    main()
