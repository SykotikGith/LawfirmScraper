"""Live verification pass for the AmLaw 100 expansion batch's ats_probe.py
hits, before adding them to config.py for real.

For Workday hits, ats_probe.py only confirmed the tenant *exists* on a
given pod -- it doesn't know the "site" slug the real WorkdayAdapter
needs (site often isn't the same as the tenant: clydeco's site is
"clydecocareers", perkinscoie's is "perkinscoieexternal"). This script
finds it by trying common guesses and looking for Workday's JSON
redirect-widget response
(`{"widget":"redirect","url":"/<site>","externalSpa":true}`), which is
a different, distinctive shape from both the generic fake-tenant error
and the path-specific-but-wrong-site error -- confirmed via live
probing on dlapiper earlier. Once the site slug is found, it fetches
real job titles via the existing WorkdayAdapter to confirm the tenant
is actually the expected company, not a name collision.

For Greenhouse, ApplicantStack, and HRMdirect hits, it fetches real job
titles the same way the original 17 firms were verified, using the
existing adapters (or the same form-submission trick discovered for
Fisher Phillips' HRMdirect board, since a plain GET returns "select
options and click Search" rather than a listing).

Usage: python -m scraper.verify_batch
Writes verify_batch_results.md alongside printing to stdout.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from .adapters.applicantstack import ApplicantStackAdapter
from .adapters.base import DEFAULT_HEADERS
from .adapters.greenhouse import GreenhouseAdapter
from .adapters.workday import WorkdayAdapter

TIMEOUT = 20

# (firm, tenant slug, pod) -- from the AmLaw 100 expansion batch's
# ats_probe.py Workday hits (July 2026 run).
WORKDAY_CANDIDATES = [
    ("McDermott Will & Emery", "mwe", "wd5"),
    ("Morrison & Foerster", "mofo", "wd5"),
    ("Skadden Arps", "skadden", "wd5"),
    ("Morgan Lewis", "morganlewis", "wd5"),
    ("Davis Polk", "davispolk", "wd5"),
    ("Hogan Lovells", "hoganlovells", "wd3"),
    ("Cleary Gottlieb", "cgsh", "wd5"),
    ("Norton Rose Fulbright", "nrf", "wd3"),
]

GREENHOUSE_CANDIDATES: list[tuple[str, str]] = []

APPLICANTSTACK_CANDIDATES: list[tuple[str, str]] = []

# Winston & Strawn's "winston" HRMdirect hit is NOT included here --
# already a CONFIRMED REJECTED collision (see REJECTED_LEADS in
# config.py: real titles there are food/manufacturing roles belonging to
# an unrelated company, "Winston Taylor"). Re-probing it would just
# reproduce the same known-wrong result. Winston & Strawn's real ATS
# still needs to be found via direct research, same as Blank Rome/
# Covington & Burling's Workday-tenant-but-no-findable-site situation.
HRMDIRECT_CANDIDATES: list[tuple[str, str]] = []

SITE_SLUG_GUESSES_TEMPLATE = [
    "{slug}",
    "{slug}careers",
    "{slug}external",
    "{slug}Careers",
    "{slug}career",
    "careers",
    "{slug}jobs",
    "{slug}-careers",
]


def find_workday_site(tenant: str, pod: str) -> str | None:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    for template in SITE_SLUG_GUESSES_TEMPLATE:
        guess = template.format(slug=tenant)
        url = f"https://{tenant}.{pod}.myworkdayjobs.com/{guess}"
        try:
            resp = session.get(url, timeout=TIMEOUT)
        except requests.exceptions.RequestException:
            continue
        if resp.status_code != 200:
            continue
        try:
            data = resp.json()
        except ValueError:
            continue
        if data.get("widget") == "redirect" and data.get("url"):
            return data["url"].lstrip("/")
    return None


def verify_workday(firm: str, tenant: str, pod: str) -> dict:
    site = find_workday_site(tenant, pod)
    if site is None:
        return {"firm": firm, "platform": f"Workday ({pod})", "status": "SITE SLUG NOT FOUND",
                "sample_titles": [], "config_snippet": None}

    adapter = WorkdayAdapter(firm, {"tenant": tenant, "wd": pod, "site": site})
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        return {"firm": firm, "platform": f"Workday ({pod})", "status": f"FETCH FAILED: {exc}",
                "sample_titles": [], "config_snippet": None}

    sample = [p.title for p in postings[:5]]
    snippet = (
        f'"{firm}": {{\n'
        f'    "adapter": WorkdayAdapter,\n'
        f'    "tenant": "{tenant}",\n'
        f'    "wd": "{pod}",\n'
        f'    "site": "{site}",\n'
        f'}},'
    )
    return {"firm": firm, "platform": f"Workday ({pod})",
            "status": f"OK -- {len(postings)} postings (site=\"{site}\")",
            "sample_titles": sample, "config_snippet": snippet}


def verify_greenhouse(firm: str, board_token: str) -> dict:
    adapter = GreenhouseAdapter(firm, {"board_token": board_token})
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        return {"firm": firm, "platform": "Greenhouse", "status": f"FETCH FAILED: {exc}",
                "sample_titles": [], "config_snippet": None}

    sample = [p.title for p in postings[:5]]
    snippet = (
        f'"{firm}": {{\n'
        f'    "adapter": GreenhouseAdapter,\n'
        f'    "board_token": "{board_token}",\n'
        f'}},'
    )
    return {"firm": firm, "platform": "Greenhouse", "status": f"OK -- {len(postings)} postings",
            "sample_titles": sample, "config_snippet": snippet}


def verify_applicantstack(firm: str, tenant: str) -> dict:
    board_url = f"https://{tenant}.applicantstack.com/x/openings"
    adapter = ApplicantStackAdapter(firm, {"board_url": board_url, "link_selector": "a[href*='/x/detail/']"})
    try:
        postings = adapter.fetch()
    except Exception as exc:  # noqa: BLE001
        return {"firm": firm, "platform": "ApplicantStack", "status": f"FETCH FAILED: {exc}",
                "sample_titles": [], "config_snippet": None}

    sample = [p.title for p in postings[:5]]
    snippet = (
        f'"{firm}": {{\n'
        f'    "adapter": ApplicantStackAdapter,\n'
        f'    "board_url": "{board_url}",\n'
        f'    "link_selector": "a[href*=\'/x/detail/\']",\n'
        f'}},'
    )
    return {"firm": firm, "platform": "ApplicantStack", "status": f"OK -- {len(postings)} postings (0 is "
            f"plausible if this firm genuinely has no ApplicantStack account despite subdomain existing)",
            "sample_titles": sample, "config_snippet": snippet}


def verify_hrmdirect(firm: str, tenant: str) -> dict:
    """HRMdirect's job-openings.php is a search FORM -- confirmed with Fisher
    Phillips -- so submit it with default/empty filters rather than GET the
    bare page."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    base_url = f"https://{tenant}.hrmdirect.com/employment/job-openings.php"
    try:
        resp = session.get(base_url, timeout=TIMEOUT)
        soup = BeautifulSoup(resp.text, "lxml")
        form = soup.find("form")
        fields = {}
        if form is not None:
            for inp in form.find_all(["input", "select"]):
                name = inp.get("name")
                if not name:
                    continue
                if inp.name == "select":
                    selected = inp.find("option", selected=True) or inp.find("option")
                    fields[name] = selected.get("value", "") if selected else ""
                else:
                    fields[name] = inp.get("value", "")
        result = session.get(base_url, params=fields, timeout=TIMEOUT)
        soup2 = BeautifulSoup(result.text, "lxml")
        titles = [
            a.get_text(strip=True)
            for a in soup2.select("a[href*='job-opening.php'], a[href*='view.php?req=']")
            if a.get_text(strip=True)
        ]
    except Exception as exc:  # noqa: BLE001
        return {"firm": firm, "platform": "HRMdirect", "status": f"FETCH FAILED: {exc}",
                "sample_titles": [], "config_snippet": None}

    snippet = (
        f'"{firm}": {{\n'
        f'    "adapter": CustomHTMLAdapter,\n'
        f'    "list_url": "{base_url}?search=true",  # verify exact query params\n'
        f'    "link_selector": "a[href*=\'job-opening.php?req=\']",\n'
        f'}},'
    )
    return {"firm": firm, "platform": "HRMdirect", "status": f"OK -- {len(titles)} job links found",
            "sample_titles": titles[:5], "config_snippet": snippet}


def main() -> None:
    results = []

    for firm, tenant, pod in WORKDAY_CANDIDATES:
        r = verify_workday(firm, tenant, pod)
        results.append(r)
        print(f"{firm}: {r['status']}")
        for t in r["sample_titles"]:
            print(f"    - {t}")

    for firm, token in GREENHOUSE_CANDIDATES:
        r = verify_greenhouse(firm, token)
        results.append(r)
        print(f"{firm}: {r['status']}")
        for t in r["sample_titles"]:
            print(f"    - {t}")

    for firm, tenant in APPLICANTSTACK_CANDIDATES:
        r = verify_applicantstack(firm, tenant)
        results.append(r)
        print(f"{firm}: {r['status']}")
        for t in r["sample_titles"]:
            print(f"    - {t}")

    for firm, tenant in HRMDIRECT_CANDIDATES:
        r = verify_hrmdirect(firm, tenant)
        results.append(r)
        print(f"{firm}: {r['status']}")
        for t in r["sample_titles"]:
            print(f"    - {t}")

    with open("verify_batch_results.md", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"## {r['firm']} ({r['platform']})\n")
            f.write(f"Status: {r['status']}\n\n")
            if r["sample_titles"]:
                f.write("Sample titles:\n")
                for t in r["sample_titles"]:
                    f.write(f"- {t}\n")
            if r["config_snippet"]:
                f.write("\nConfig snippet:\n```python\n")
                f.write(r["config_snippet"])
                f.write("\n```\n")
            f.write("\n")

    print("\nWritten to verify_batch_results.md")


if __name__ == "__main__":
    main()
