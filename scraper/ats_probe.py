"""One-shot ATS platform detector for a batch of firms not yet in config.py.

For each firm, tries each slug candidate against a fixed set of URL
patterns for the ATS platforms already confirmed elsewhere in this
project, and reports the first pattern that returns a real (non-404,
non-connection-error) response.

IMPORTANT: this only checks host/path reachability -- it does NOT parse
job listings, and it does NOT confirm the tenant actually belongs to the
expected company. A generic slug guess can collide with an unrelated
organization on a shared platform host (e.g. some other "cooley" on
Greenhouse). Treat every hit here as a lead to verify, not a confirmed
adapter config -- the same way Wilson Elser's real ATS (Greenhouse) and
Baker McKenzie's (Avature, not Oracle) turned out to differ from the
first guess earlier in this project.

Workday detection hits the bare tenant root (no site path), since we
don't know each firm's site slug yet -- a "needs manual check" result
doesn't rule out Workday entirely; it might just need the right
pod number/site name once someone digs further (this happened with
Perkins Coie: wd1 gave a real-but-wrong-pod error, wd115 was correct).

Usage: python -m scraper.ats_probe
Writes ats_probe_results.md alongside printing the table to stdout.
"""
from __future__ import annotations

import concurrent.futures
import sys

import requests

from .adapters.base import DEFAULT_HEADERS

TIMEOUT = 8
MAX_WORKERS = 12

# (firm name, [slug candidates])
FIRMS: list[tuple[str, list[str]]] = [
    ("Kirkland & Ellis", ["kirkland"]),
    ("Latham & Watkins", ["lw"]),
    ("Skadden Arps", ["skadden"]),
    ("Gibson Dunn", ["gibsondunn"]),
    ("Sidley Austin", ["sidley"]),
    ("Ropes & Gray", ["ropesgray"]),
    ("White & Case", ["whitecase"]),
    ("Morgan Lewis", ["morganlewis"]),
    ("Simpson Thacher", ["simpsonthacher", "stblaw"]),
    ("Wachtell Lipton", ["wlrk"]),
    ("Davis Polk", ["davispolk"]),
    ("Quinn Emanuel", ["quinnemanuel"]),
    ("Paul Weiss", ["paulweiss"]),
    ("Paul Hastings", ["paulhastings"]),
    ("Dentons", ["dentons"]),
    ("Jones Day", ["jonesday"]),
    ("Hogan Lovells", ["hoganlovells"]),
    ("Sullivan & Cromwell", ["sullcrom"]),
    ("Weil Gotshal", ["weil"]),
    ("Cleary Gottlieb", ["cgsh", "cleary"]),
    ("Debevoise & Plimpton", ["debevoise"]),
    ("Milbank", ["milbank"]),
    ("Willkie Farr", ["willkie"]),
    ("Cooley", ["cooley"]),
    ("Wilson Sonsini", ["wsgr"]),
    ("Goodwin Procter", ["goodwinlaw", "goodwin"]),
    ("WilmerHale", ["wilmerhale"]),
    ("McDermott Will & Emery", ["mwe"]),
    ("K&L Gates", ["klgates"]),
    ("Greenberg Traurig", ["gtlaw"]),
    ("Akin Gump", ["akingump"]),
    ("Vinson & Elkins", ["velaw"]),
    ("Norton Rose Fulbright", ["nortonrosefulbright", "nrf"]),
    ("Squire Patton Boggs", ["squirepattonboggs"]),
    ("Mayer Brown", ["mayerbrown"]),
    ("Winston & Strawn", ["winston"]),
    ("Katten Muchin", ["katten"]),
    ("Alston & Bird", ["alston"]),
    ("Nelson Mullins", ["nelsonmullins"]),
    ("Troutman Pepper Locke", ["troutmanpepperlocke", "troutman"]),
    ("Faegre Drinker", ["faegredrinker"]),
    ("Bryan Cave Leighton Paisner", ["bclplaw", "bcl"]),
    ("Holland & Knight", ["hklaw"]),
    ("Baker Donelson", ["bakerdonelson"]),
    ("Ogletree Deakins", ["ogletree"]),
    ("Jackson Lewis", ["jacksonlewis"]),
    ("Fox Rothschild", ["foxrothschild"]),
    ("Duane Morris", ["duanemorris"]),
    ("Blank Rome", ["blankrome"]),
    ("Proskauer Rose", ["proskauer"]),
    ("Kramer Levin", ["kramerlevin"]),
    ("Arnold & Porter", ["arnoldporter"]),
    ("Crowell & Moring", ["crowell"]),
    ("Covington & Burling", ["cov", "covington"]),
    ("Hunton Andrews Kurth", ["huntonak"]),
    ("Venable", ["venable"]),
    ("Dechert", ["dechert"]),
    ("Schulte Roth & Zabel", ["srz"]),
    ("O'Melveny & Myers", ["omm"]),
    ("Munger Tolles", ["mto"]),
    ("Fenwick & West", ["fenwick"]),
    ("Morrison & Foerster", ["mofo"]),
    ("Sheppard Mullin", ["sheppardmullin"]),
    ("Davis Wright Tremaine", ["dwt"]),
    ("King & Spalding", ["kslaw"]),
    ("Eversheds Sutherland", ["evershedssutherland", "eversheds"]),
    ("Bracewell", ["bracewell"]),
    ("Locke Lord", ["lockelord"]),
    ("Haynes and Boone", ["haynesboone"]),
]

PATTERNS: list[tuple[str, str]] = [
    ("Workday (wd1)", "https://{slug}.wd1.myworkdayjobs.com/"),
    ("Workday (wd103)", "https://{slug}.wd103.myworkdayjobs.com/"),
    ("Workday (wd115)", "https://{slug}.wd115.myworkdayjobs.com/"),
    ("iCIMS", "https://careers-{slug}.icims.com/"),
    ("ApplicantStack", "https://{slug}.applicantstack.com/"),
    ("HRMdirect", "https://{slug}.hrmdirect.com/"),
    ("Greenhouse", "https://job-boards.greenhouse.io/{slug}"),
]


def probe_url(url: str) -> tuple[int | None, str | None]:
    """Return (status_code, error). error is None for any real HTTP
    response (even 403/404); it's set only for connection-level failures
    (DNS resolution, timeout, refused connection, etc.)."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, None
    except requests.exceptions.RequestException as exc:
        return None, type(exc).__name__


def confidence_for(status: int) -> str:
    if status == 200:
        return "High"
    if 300 <= status < 400:
        return "Medium-High (redirect)"
    if status == 403:
        return "Medium (blocked, likely exists)"
    return "Low"


def probe_firm(firm: str, slugs: list[str]) -> dict:
    for slug in slugs:
        for label, template in PATTERNS:
            url = template.format(slug=slug)
            status, error = probe_url(url)
            if error is not None or status == 404:
                continue
            return {
                "firm": firm,
                "platform": label,
                "url": url,
                "status": status,
                "confidence": confidence_for(status),
            }
    return {"firm": firm, "platform": "needs manual check", "url": "", "status": None, "confidence": "-"}


def main() -> None:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(probe_firm, firm, slugs): firm for firm, slugs in FIRMS}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            print(
                f"[{done}/{len(FIRMS)}] {result['firm']}: {result['platform']} "
                f"({result['status']}) {result['url']}",
                file=sys.stderr,
            )

    order = {firm: i for i, (firm, _) in enumerate(FIRMS)}
    results.sort(key=lambda r: order[r["firm"]])

    lines = ["| Firm | Detected Platform | Working URL | Confidence |", "|---|---|---|---|"]
    for r in results:
        url = r["url"] or "-"
        lines.append(f"| {r['firm']} | {r['platform']} | {url} | {r['confidence']} |")

    table = "\n".join(lines)
    print("\n" + table)

    with open("ats_probe_results.md", "w", encoding="utf-8") as f:
        f.write(table + "\n")
    print("\nWritten to ats_probe_results.md", file=sys.stderr)


if __name__ == "__main__":
    main()
