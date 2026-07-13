"""AmLaw 100 batch, round 3: for the 37 firms that showed zero ATS signal
on the round-2 broad sniff (bare domain + 3 guessed careers paths), try a
more scalable discovery technique instead of guessing more paths blind:
check each firm's XML sitemap for any URL containing "career" or "job",
then immediately scan whatever's found for a known ATS platform in the
same pass -- discovery and verification combined, to avoid yet another
back-and-forth round just to find the right path.

Handles both a flat sitemap (<url><loc>...) and a sitemap INDEX (nested
<sitemap><loc>...pointing at sub-sitemaps) -- for an index, sub-sitemaps
whose own URL contains "career"/"job" are fetched one level deeper.

Usage: python -m scraper.diagnose
Writes diagnose_results.md alongside printing progress to stderr and the
final table to stdout.
"""
from __future__ import annotations

import concurrent.futures
import re
import sys

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 15
MAX_WORKERS = 10
SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
CAREER_KEYWORD_RE = re.compile(r"career|/job", re.IGNORECASE)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)

# (firm, domain guess) -- the 37 firms with zero signal from round 2, reusing
# the same domain guesses (mostly confirmed correct -- these were 200s, not
# 404s, so the domain itself usually wasn't the problem).
FIRMS: list[tuple[str, str]] = [
    ("Kirkland & Ellis", "www.kirkland.com"),
    ("Latham & Watkins", "www.lw.com"),
    ("Sidley Austin", "www.sidley.com"),
    ("Wachtell Lipton", "www.wlrk.com"),
    ("Quinn Emanuel", "www.quinnemanuel.com"),
    ("Paul Weiss", "www.paulweiss.com"),
    ("Dentons", "www.dentons.com"),
    ("Jones Day", "www.jonesday.com"),
    ("Sullivan & Cromwell", "www.sullcrom.com"),
    ("Wilson Sonsini", "www.wsgr.com"),
    ("WilmerHale", "www.wilmerhale.com"),
    ("K&L Gates", "www.klgates.com"),
    ("Vinson & Elkins", "www.velaw.com"),
    ("Squire Patton Boggs", "www.squirepattonboggs.com"),
    ("Mayer Brown", "www.mayerbrown.com"),
    ("Baker Donelson", "www.bakerdonelson.com"),
    ("Ogletree Deakins", "www.ogletree.com"),
    ("Fox Rothschild", "www.foxrothschild.com"),
    ("Duane Morris", "www.duanemorris.com"),
    ("Proskauer Rose", "www.proskauer.com"),
    ("Kramer Levin", "www.kramerlevin.com"),
    ("Arnold & Porter", "www.arnoldporter.com"),
    ("Crowell & Moring", "www.crowell.com"),
    ("Hunton Andrews Kurth", "www.huntonak.com"),
    ("Venable", "www.venable.com"),
    ("Munger Tolles", "www.mto.com"),
    ("Sheppard Mullin", "www.sheppardmullin.com"),
    ("Bracewell", "www.bracewell.com"),
    ("Willkie Farr & Gallagher", "www.willkie.com"),
    ("Eversheds Sutherland", "www.eversheds-sutherland.com"),
    ("Dechert", "www.dechert.com"),
    ("Akin Gump", "www.akingump.com"),
    ("Baker Hostetler", "www.bakerlaw.com"),
    ("Katten Muchin Rosenman", "www.katten.com"),
    ("Baker Botts", "www.bakerbotts.com"),
    ("Mintz Levin", "www.mintz.com"),
    ("Winston & Strawn", "www.winston.com"),
]

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


def fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.text


def find_sitemap_career_urls(domain: str) -> list[str]:
    for path in SITEMAP_PATHS:
        text = fetch(f"https://{domain}{path}")
        if text is None:
            continue
        locs = LOC_RE.findall(text)
        if not locs:
            continue
        career_locs = [loc for loc in locs if CAREER_KEYWORD_RE.search(loc)]
        if career_locs:
            return career_locs[:5]
        # sitemap index case: no direct career URLs, but a sub-sitemap's own
        # URL might mention career/jobs -- fetch one level deeper.
        sub_sitemaps = [loc for loc in locs if CAREER_KEYWORD_RE.search(loc) or "sitemap" in loc.lower()]
        for sub in sub_sitemaps[:3]:
            sub_text = fetch(sub)
            if sub_text is None:
                continue
            sub_locs = LOC_RE.findall(sub_text)
            sub_career_locs = [loc for loc in sub_locs if CAREER_KEYWORD_RE.search(loc)]
            if sub_career_locs:
                return sub_career_locs[:5]
        return []
    return []


def scan_for_ats(url: str) -> tuple[str | None, str | None]:
    text = fetch(url)
    if text is None:
        return None, None
    for label, pattern in ATS_DOMAIN_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            idx = match.start()
            return label, text[max(0, idx - 100):idx + 150]
    return "no signal", None


def process_firm(firm: str, domain: str) -> dict:
    career_urls = find_sitemap_career_urls(domain)
    if not career_urls:
        return {"firm": firm, "domain": domain, "sitemap_urls": [], "platform": "no sitemap career URLs found", "context": None}

    for url in career_urls:
        platform, context = scan_for_ats(url)
        if platform and platform != "no signal":
            return {"firm": firm, "domain": domain, "sitemap_urls": career_urls, "platform": platform,
                     "context": context, "hit_url": url}

    return {"firm": firm, "domain": domain, "sitemap_urls": career_urls,
            "platform": "sitemap URLs found but no ATS signal", "context": None}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(process_firm, firm, domain): firm for firm, domain in FIRMS}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            print(f"[{done}/{len(FIRMS)}] {result['firm']}: {result['platform']}"
                  f"{' -- ' + result.get('hit_url', '') if result.get('hit_url') else ''}", file=sys.stderr)

    order = {firm: i for i, (firm, _) in enumerate(FIRMS)}
    results.sort(key=lambda r: order[r["firm"]])

    lines = ["| Firm | Domain | Sitemap career URLs found | Platform |", "|---|---|---|---|"]
    for r in results:
        urls_str = "; ".join(r["sitemap_urls"][:2]) if r["sitemap_urls"] else "-"
        lines.append(f"| {r['firm']} | {r['domain']} | {urls_str} | {r['platform']} |")
    table = "\n".join(lines)
    print("\n" + table)

    with open("diagnose_results.md", "w", encoding="utf-8") as f:
        f.write(table + "\n\n")
        for r in results:
            f.write(f"## {r['firm']} ({r['domain']})\n")
            f.write(f"Platform: {r['platform']}\n")
            if r.get("hit_url"):
                f.write(f"Hit URL: {r['hit_url']}\n")
            if r["context"]:
                f.write(f"Context: ...{r['context']}...\n")
            if r["sitemap_urls"]:
                f.write("All sitemap career URLs found:\n")
                for u in r["sitemap_urls"]:
                    f.write(f"- {u}\n")
            f.write("\n")
    print("\nWritten to diagnose_results.md", file=sys.stderr)


if __name__ == "__main__":
    main()
