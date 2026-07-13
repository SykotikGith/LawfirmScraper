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

ApplicantStack has a subtler version of the same problem: a fake slug
still returns HTTP 200 (status code alone is useless here), but silently
redirects to a generic https://www.applicantstack.com/job-not-found/
marketing page instead of the tenant's own /public/login page -- a real
tenant (confirmed with hinshawlaw) stays on its own subdomain. So
ApplicantStack hits are validated by checking the final URL after
redirects, not just the status code.

HRMdirect and Greenhouse were checked the same way (known-real vs
known-fake slugs) and cleanly return 404 for fake slugs -- no special
handling needed there.

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
# wd1-wd10 covers the standard pod range; wd103/wd115 kept in because two
# confirmed-real tenants in this project (Clyde & Co, Perkins Coie) sit on
# non-standard pods outside wd1-wd10 -- dropping them would've missed both.
WORKDAY_PODS = [f"wd{n}" for n in range(1, 11)] + ["wd103", "wd115"]
_WORKDAY_PROBE_PATH = "ats-probe-nonexistent-path-check"
_WORKDAY_TENANT_EXISTS_MARKER = "Requested page not found"

# AmLaw 100 expansion batch (July 2026). Firms already resolved in
# config.py are deliberately NOT here (re-probing them wastes requests and
# risks confusing already-documented results): Troutman Pepper Locke,
# White & Case, Fenwick & West (FIRMS -- confirmed Workday); Ropes & Gray,
# Blank Rome, Covington & Burling, Weil Gotshal (MANUAL_CHECK_FIRMS --
# already investigated and documented); Locke Lord (superseded by the
# Troutman Pepper Locke merger, see that FIRMS entry's note).
#
# "McDermott Will & Schulte" from the request doesn't match any real AmLaw
# firm name -- assumed to mean McDermott Will & Emery (already listed
# below); "Schulte" is likely cross-contamination from Schulte Roth &
# Zabel, a separate firm also in this list. Flagged for the user to
# confirm/correct.
#
# (firm name, [slug candidates])
FIRMS: list[tuple[str, list[str]]] = [
    # --- Priority (Maegan's personally supported firms) ---
    ("McDermott Will & Emery", ["mwe"]),
    ("Willkie Farr & Gallagher", ["willkie"]),
    ("Eversheds Sutherland", ["evershedssutherland", "eversheds"]),
    ("Dechert", ["dechert"]),
    ("Morrison & Foerster", ["mofo"]),
    ("Akin Gump", ["akingump"]),
    ("Foley & Lardner", ["foley", "foleylardner"]),
    ("Faegre Drinker", ["faegredrinker"]),
    ("Baker Hostetler", ["bakerhostetler", "bakerlaw"]),
    ("Katten Muchin Rosenman", ["katten"]),
    ("Baker Botts", ["bakerbotts"]),
    ("Mintz Levin", ["mintz", "mintzlevin"]),
    # --- Remaining ---
    ("Kirkland & Ellis", ["kirkland"]),
    ("Latham & Watkins", ["lw"]),
    ("Skadden Arps", ["skadden"]),
    ("Sidley Austin", ["sidley"]),
    ("Morgan Lewis", ["morganlewis"]),
    ("Wachtell Lipton", ["wlrk"]),
    ("Davis Polk", ["davispolk"]),
    ("Quinn Emanuel", ["quinnemanuel"]),
    ("Paul Weiss", ["paulweiss"]),
    ("Dentons", ["dentons"]),
    ("Jones Day", ["jonesday"]),
    ("Hogan Lovells", ["hoganlovells"]),
    ("Sullivan & Cromwell", ["sullcrom"]),
    ("Cleary Gottlieb", ["cgsh", "cleary"]),
    ("Wilson Sonsini", ["wsgr"]),
    ("WilmerHale", ["wilmerhale"]),
    ("K&L Gates", ["klgates"]),
    ("Vinson & Elkins", ["velaw"]),
    ("Norton Rose Fulbright", ["nortonrosefulbright", "nrf"]),
    ("Squire Patton Boggs", ["squirepattonboggs"]),
    ("Mayer Brown", ["mayerbrown"]),
    # "winston" alone is a KNOWN REJECTED collision on HRMdirect (see
    # REJECTED_LEADS in config.py -- an unrelated food/manufacturing
    # company, "Winston Taylor"). winstonstrawn tried first; if that
    # doesn't hit and this falls through to "winston" again, that's the
    # same false positive resurfacing, not new signal -- don't re-add it.
    ("Winston & Strawn", ["winstonstrawn", "winston"]),
    ("Nelson Mullins", ["nelsonmullins"]),
    ("Bryan Cave Leighton Paisner", ["bclplaw", "bcl"]),
    ("Baker Donelson", ["bakerdonelson"]),
    ("Ogletree Deakins", ["ogletree"]),
    ("Fox Rothschild", ["foxrothschild"]),
    ("Duane Morris", ["duanemorris"]),
    ("Proskauer Rose", ["proskauer"]),
    ("Kramer Levin", ["kramerlevin"]),
    ("Arnold & Porter", ["arnoldporter"]),
    ("Crowell & Moring", ["crowell"]),
    ("Hunton Andrews Kurth", ["huntonak"]),
    ("Venable", ["venable"]),
    ("Munger Tolles", ["mto"]),
    ("Sheppard Mullin", ["sheppardmullin"]),
    ("Davis Wright Tremaine", ["dwt"]),
    ("Bracewell", ["bracewell"]),
]

PATTERNS: list[tuple[str, str]] = [
    # iCIMS deliberately excluded -- see module docstring. It sits behind
    # an AWS WAF challenge that responds identically for real and fake
    # tenants, so a "hit" here is not real signal.
    #
    # Oracle Recruiting Cloud and UKG/UltiPro are ALSO deliberately
    # excluded from bulk slug-guessing, unlike Workday/Greenhouse/
    # ApplicantStack/HRMdirect: neither has a predictable {slug}.platform
    # domain pattern to guess against. Oracle tenants live at a
    # firm-specific host (e.g. hctq.fa.us2.oraclecloud.com for Cozen
    # O'Connor) with a region code and site number that vary per tenant
    # and aren't derivable from the firm name. UltiPro job boards live at
    # recruiting.ultipro.com/<CompanyCode>/JobBoard/<opaque-GUID>/ -- the
    # GUID can't be guessed at all. Both platforms only became findable
    # for Cozen O'Connor and Akerman via direct research (an already-known
    # URL), not slug-guessing -- any firm actually on one of these
    # platforms will fall through to "needs manual check" here and need
    # the same direct-research treatment.
    ("ApplicantStack", "https://{slug}.applicantstack.com/"),
    ("HRMdirect", "https://{slug}.hrmdirect.com/"),
    ("Greenhouse", "https://job-boards.greenhouse.io/{slug}"),
]

# Platform label -> substring that, if present in the FINAL url after
# redirects, means we got bounced to a generic "not found" page rather
# than a real tenant, even though the status code was 200.
REJECT_IF_REDIRECTED_TO = {
    "ApplicantStack": "job-not-found",
}


def probe_url(url: str) -> tuple[int | None, str | None, str | None, str | None]:
    """Return (status_code, body, final_url, error). error is None for any
    real HTTP response (even 403/404); it's set only for connection-level
    failures (DNS resolution, timeout, refused connection, etc.)."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, resp.url, None
    except requests.exceptions.RequestException as exc:
        return None, None, None, type(exc).__name__


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
        status, body, _final_url, error = probe_url(url)
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
            status, _body, final_url, error = probe_url(url)
            if error is not None or status == 404:
                continue
            reject_marker = REJECT_IF_REDIRECTED_TO.get(label)
            if reject_marker and final_url is not None and reject_marker in final_url:
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
