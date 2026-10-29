"""Build the committed demo copy of the Resources library (fixtures/resources/).

    python -m scripts.seed_resources

The library proper lives in data/resources/ (git-ignored), so a fresh clone starts with nothing to read. This writes:
  * the findings, trends and official figures of the committed demo snapshots (fixtures/evidence/), and
  * a short curated list of price-sensitivity references, each with a quote that was checked against the page's own text
    on the retrieval date.
Everything here is reference only; none of it moves a prior. Re-running replaces the files.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.evidence import resources
from backend.evidence.models import EvidenceSnapshot
from backend.evidence.store import DEMO_DIR, SEED_RESOURCES_DIR

RETRIEVED = "2026-10-29T00:00:00+00:00"
MATHER = "https://www.mathereconomics.com/price-elasticity-tests-yield-revenue-opportunities-for-publishers/"
APPSOPS = "https://appsops.store/blog/ios-subscription-price-elasticity-research"

# (claim, quote, url). Quotes were checked against the page text on RETRIEVED. These are about news readers and app
# stores, not students, which each claim says; they are shown so a founder can read them, never used as a prior.
CURATED = [
    ("Renewal price tests on digital-only news subscribers (not students, not software): about -0.05, i.e. 0.5% of "
     "subscribers stop per 10% price rise. A consultancy's result from its own clients' data.",
     "we found the price elasticity of these digital-only subscribers was approximately -.05", MATHER),
    ("Same source: engaged readers were about a quarter as price-sensitive as non-engaged ones.",
     "had price elasticity that was one-quarter the level of non-engaged digital subscribers", MATHER),
    ("A blog on iOS subscription apps says there is no single elasticity: acquisition and renewal respond differently.",
     "Subscription price elasticity is not a single number", APPSOPS),
    ("The same blog, citing RevenueCat and Sensor Tower, lists categories that are less price-sensitive when "
     "acquiring customers, education among them.",
     "Productivity and utilities, health and fitness, professional tools, education", APPSOPS),
    ("The same blog's own caveat on its evidence.",
     "That makes the evidence directional rather than causal", APPSOPS),
]


def main(out: Path = SEED_RESOURCES_DIR) -> int:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()
    total = 0
    for f in sorted(DEMO_DIR.glob("ev_*_demo.json")):
        total += resources.add(EvidenceSnapshot.model_validate_json(f.read_text()), out)
    pack, geography = "saas", "global"
    items = [resources.Resource(
        id=resources._id(pack, geography, url, quote), topic="price sensitivity", claim=claim, quote=quote, url=url,
        domain=resources._domain(url), pack=pack, geography=geography, retrieved_at=RETRIEVED,
        snapshot_id="curated_price_sensitivity") for claim, quote, url in CURATED]
    resources._file(out, pack, geography).write_text(json.dumps([r.model_dump() for r in items], indent=2))
    print(f"{total + len(items)} entries in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
