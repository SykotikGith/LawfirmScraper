"""AmLaw 100 batch, round 2: broad ATS-platform sniff for the 42 firms
that returned zero signal in ats_probe.py's slug-guessing pass (every
platform tried, Workday checked across wd1-wd10 + wd103 + wd115).

Same technique that found Norton Rose Fulbright's real Workday link and
that identified the 6 dormant-Workday firms' real platforms (or lack
thereof): fetch each firm's own marketing site and scan the raw HTML for
ANY known ATS platform domain, rather than keep guessing ATS-specific
subdomain patterns blind. Checks the bare domain plus a few common
careers-page paths, concurrently across all 42 firms.

Domain guesses below are UNVERIFIED -- a 404/connection failure on all
paths for a firm usually just means the domain guess itself is wrong,
not that the firm has no findable ATS; those need a corrected domain on
a follow-up round, not necessarily a "needs manual check" verdict.

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
MAX_WORKERS = 12
CAREER_PATHS = ["", "/careers", "/en/careers", "/en-us/careers"]

# (firm, domain guess)
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
    ("Nelson Mullins", "www.nelsonmullins.com"),
    ("Bryan Cave Leighton Paisner", "www.bclplaw.com"),
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
    ("Davis Wright Tremaine", "www.dwt.com"),
    ("Bracewell", "www.bracewell.com"),
    ("Willkie Farr & Gallagher", "www.willkie.com"),
    ("Eversheds Sutherland", "www.eversheds-sutherland.com"),
    ("Dechert", "www.dechert.com"),
    ("Akin Gump", "www.akingump.com"),
    ("Foley & Lardner", "www.foley.com"),
    ("Faegre Drinker", "www.faegredrinker.com"),
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
    "Phenom": r"phenompeople\.com",
    "SmartRecruiters": r"smartrecruiters\.com",
    "Taleo": r"taleo\.net",
    "SuccessFactors": r"successfactors\.com",
    "Avature": r"avature\.net",
    "Jobvite": r"jobvite\.com",
    "Lever": r"jobs\.lever\.co",
    "BambooHR": r"bamboohr\.com",
    "Workday (any format)": r"myworkday(?:jobs|site)\.com",
}


def scan_firm(firm: str, domain: str) -> dict:
    tried = []
    for path in CAREER_PATHS:
        url = f"https://{domain}{path}"
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        except requests.exceptions.RequestException as exc:
            tried.append(f"{url} -> EXCEPTION {type(exc).__name__}")
            continue
        tried.append(f"{url} -> {resp.status_code} (final: {resp.url}, len={len(resp.text)})")
        if resp.status_code >= 400:
            continue

        text = resp.text
        for label, pattern in ATS_DOMAIN_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                idx = match.start()
                context = text[max(0, idx - 100):idx + 150]
                return {
                    "firm": firm, "domain": domain, "platform": label, "url": url,
                    "final_url": resp.url, "context": context, "tried": tried,
                }
    return {"firm": firm, "domain": domain, "platform": "no signal", "url": None,
            "final_url": None, "context": None, "tried": tried}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(scan_firm, firm, domain): firm for firm, domain in FIRMS}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            print(f"[{done}/{len(FIRMS)}] {result['firm']}: {result['platform']}"
                  f"{' -- ' + result['final_url'] if result['final_url'] else ''}", file=sys.stderr)

    order = {firm: i for i, (firm, _) in enumerate(FIRMS)}
    results.sort(key=lambda r: order[r["firm"]])

    lines = ["| Firm | Domain guess | Platform found | Final URL |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['firm']} | {r['domain']} | {r['platform']} | {r['final_url'] or '-'} |")
    table = "\n".join(lines)
    print("\n" + table)

    with open("diagnose_results.md", "w", encoding="utf-8") as f:
        f.write(table + "\n\n")
        for r in results:
            f.write(f"## {r['firm']} ({r['domain']})\n")
            f.write(f"Platform: {r['platform']}\n")
            if r["final_url"]:
                f.write(f"Final URL: {r['final_url']}\n")
            if r["context"]:
                f.write(f"Context: ...{r['context']}...\n")
            f.write("Paths tried:\n")
            for t in r["tried"]:
                f.write(f"- {t}\n")
            f.write("\n")
    print("\nWritten to diagnose_results.md", file=sys.stderr)


if __name__ == "__main__":
    main()
