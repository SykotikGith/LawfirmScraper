# Squirrel Notes

Not things to build next. Things Future Maegan shouldn't have to remember.

## Parked ideas

**Repo/project rename**
"LawFirmScraper" undersells it. Consider "Legal Tech Role Radar" or similar once the
pipeline's stable. Requires updating the GitHub Pages URL and Actions workflow refs.

**Multi-user profiles**
YAML per person (e.g. `profiles/maegan.yaml`, `profiles/aly.yaml`), one scraping
engine, swappable keyword lens. Good architecture, deferred until the core is fully
proven for me. Needs per-profile state tracking, per-profile hosting, and a real
privacy conversation before adding anyone else's search activity to a public repo.

**Match scoring/weighting**
Explicitly rejected for now. Fake precision at current volume (~9 matches/run).
Revisit only if match volume grows substantially (post-AmLaw 200, maybe).

**Historical trend metrics**
Jobs by category over time, etc. Needs weeks of accumulated run history to mean
anything. Not viable yet. Revisit in a couple months once there's real history.

**AmLaw 200 expansion**
Deferred until AmLaw 100 is fully scoped with the pipeline-health dashboard in
place. Diminishing returns risk: smaller firms, less KM/AI infrastructure investment.

**iCIMS WAF block**
Lewis Brisbois, Gordon Rees, Orrick, Milbank all blocked by AWS WAF bot challenge.
Currently flagged "manual check needed" (Option 3 from our discussion). Playwright/
browser automation would unblock it, one-time cost that pays off across every
iCIMS tenant at once. Not urgent, easy to revisit if the need arises.

## In progress (as of this note)

- AmLaw 100 expansion, Wave 1 (firms I've personally supported) then Wave 2
- Remote/hybrid/onsite detection and hard-exclude for onsite/hybrid
- Pipeline health dashboard (adapter failures, manual-review firms, no-postings firms)
