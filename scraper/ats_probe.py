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

Workday detection: myworkdayjobs.com is wildcard-DNS'd to a shared
Cloudflare edge, so both DNS resolution and a bare-root "/" GET are
IDENTICAL for a real tenant and a completely made-up one -- confirmed by
live probing (thisisnotarealfirmxyz123.wd1.myworkdayjobs.com resolves to
the same IP and returns the same blank 406 as dlapiper's real tenant).
Neither can be used for detection. What DOES differentiate them: hitting
ANY throwaway path under a tenant that actually exists on that pod
returns a path-specific Workday application error
("Requested page not found /whatever-you-asked"), while a tenant that
doesn't exist on that pod (fake, or real-but-wrong-pod) returns an
identical generic fallback ("Internal Server Error. (id: )", always the
same byte length) no matter what path is requested. So we only need one
throwaway path per pod to confirm tenant existence -- no need to guess
the real site slug at all.

iCIMS detection is NOT attempted here, unlike Workday. careers-{slug}.icims.com
sits behind an AWS WAF "Human Verification" challenge that returns a
BYTE-FOR-BYTE IDENTICAL 405 page (confirmed via live probing: same DNS
edge IP range, same 2115-byte body) whether the tenant is one of our 3
confirmed-real ones (grsm, lewisbrisbois, orrick) or a completely
made-up slug. Unlike Workday's wrong-pod case, there's no legitimate
app-layer response to fall back on here -- WAF challenges are designed
specifically to look identical regardless of the underlying resource, so
there is no reliable way to confirm an iCIMS tenant via plain HTTP
probing. Our 3 known iCIMS tenants were confirmed via external
corroboration (indexed job posting URLs), not by hitting the tenant
directly -- that's the only reliable method for this platform short of
solving the WAF challenge with real browser automation.

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
WORKDAY_PODS = ["wd1", "wd103", "wd115"]
_WORKDAY_PROBE_PATH = "ats-probe-nonexistent-path-check"
_WORKDAY_TENANT_EXISTS_MARKER = "Requested page not found"

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
    # iCIMS deliberately excluded -- see module docstring. It sits behind
    # an AWS WAF challenge that responds identically for real and fake
    # tenants, so a "hit" here is not real signal.
    ("ApplicantStack", "https://{slug}.applicantstack.com/"),
    ("HRMdirect", "https://{slug}.hrmdirect.com/"),
    ("Greenhouse", "https://job-boards.greenhouse.io/{slug}"),
]


def probe_url(url: str) -> tuple[int | None, str | None, str | None]:
    """Return (status_code, body, error). error is None for any real HTTP
    response (even 403/404); it's set only for connection-level failures
    (DNS resolution, timeout, refused connection, etc.)."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except requests.exceptions.RequestException as exc:
        return None, None, type(exc).__name__


def confidence_for(status: int) -> str:
    if status == 200:
        return "High"
    if 300 <= status < 400:
        return "Medium-High (redirect)"
    if status == 403:
        return "Medium (blocked, likely exists)"
    return "Low"


def probe_workday(slug: str) -> dict | None:
    """Check whether `slug` is a real Workday tenant on any of WORKDAY_PODS,
    using the path-specific-vs-generic-error signal described in the module
    docstring. Returns a result dict on a confirmed hit, else None."""
    for pod in WORKDAY_PODS:
        url = f"https://{slug}.{pod}.myworkdayjobs.com/{_WORKDAY_PROBE_PATH}"
        status, body, error = probe_url(url)
        if error is not None or status != 200 or body is None:
            continue
        if _WORKDAY_TENANT_EXISTS_MARKER in body:
            return {
                "firm": None,  # filled in by caller
                "platform": f"Workday ({pod})",
                "url": f"https://{slug}.{pod}.myworkdayjobs.com/",
                "status": status,
                "confidence": "High (tenant confirmed via path-specific error)",
            }
    return None


def probe_firm(firm: str, slugs: list[str]) -> dict:
    for slug in slugs:
        workday_hit = probe_workday(slug)
        if workday_hit is not None:
            workday_hit["firm"] = firm
            return workday_hit

        for label, template in PATTERNS:
            url = template.format(slug=slug)
            status, _body, error = probe_url(url)
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
