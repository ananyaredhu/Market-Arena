"""Audit of a pack's priors: what each one is, where it comes from, and how much it matters (Person A).

    python -m scripts.prior_audit                 # saas -> docs/eval/prior_audit.md
    python -m scripts.prior_audit --pack cafe

For every prior class it multiplies the ranges by 0.75 and by 1.25 (one class at a time, all segments), runs the
pack's own demo product on the same customers and seed, and reports how far the demo product's simulated share
moves. It also asks what happens if the new product were already known (a brand score for it). No language model is
involved.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean

from backend.engine.engine import run_scenario
from backend.population.generator import _build
from backend.population.models import PackSpec, PopulationRequest
from backend.population.packs import load_pack

OUT = Path(__file__).resolve().parents[1] / "docs" / "eval"
SEEDS, REPEATS, AGENTS = (1, 2, 3), 15, 300
CLASSES = ["budget", "alpha", "w", "switch", "risk", "outside_utility", "tau", "brand"]
MEANING = {
    "budget": "what a customer can spend per period", "alpha": "price sensitivity", "w": "weight on each feature",
    "switch": "cost of leaving what they use now", "risk": "dislike of trying something new",
    "outside_utility": "appeal of doing nothing / a free tool", "tau": "how random choices are",
    "brand": "pull of a known competitor (the new product starts at 0)",
}


def scaled(pack: PackSpec, cls: str, k: float) -> PackSpec:
    """A copy of the pack with every range of one prior class multiplied by k (weights stay within 0 to 1)."""
    spec = pack.model_copy(deep=True)

    def rng(r, hi=None):
        lo, up = r[0] * k, r[1] * k
        return (min(lo, hi), min(up, hi)) if hi is not None else (lo, up)

    for s in spec.segments:
        p = s.priors
        if cls == "w":
            p.w = {a: rng(r, 1.0) for a, r in p.w.items()}
        elif cls == "brand":
            p.brand = {o: rng(r, 1.0) for o, r in p.brand.items()}
        else:
            setattr(p, cls, rng(getattr(p, cls)))
    return spec


def with_known_brand(pack: PackSpec, level: float) -> PackSpec:
    spec = pack.model_copy(deep=True)
    for s in spec.segments:
        s.priors.brand = {**s.priors.brand, "you": (level, level)}
    return spec


def share(pack: PackSpec, spec: PackSpec) -> float:
    ids = ["you", *[c["id"] for c in pack.competitors]]
    options = [pack.demo_product, *pack.competitors, {"id": pack.outside_id, "label": "Do nothing", "role": "outside"}]
    out = []
    for seed in SEEDS:
        pop = _build(pack, spec, PopulationRequest(pack=pack.pack, n_agents=AGENTS, seed=seed), ids)
        out.append(run_scenario(pop["agents"], options, seed, repeats=REPEATS)["totals"]["you"]["p50"])
    return mean(out)


def audit(pack_name: str) -> str:
    pack = load_pack(pack_name)
    base = share(pack, pack)
    rows = []
    for cls in CLASSES:
        lo, hi = share(pack, scaled(pack, cls, 0.75)) - base, share(pack, scaled(pack, cls, 1.25)) - base
        rows.append((cls, lo, hi))
    known = {lv: share(pack, with_known_brand(pack, lv)) - base for lv in (0.2, 0.4)}
    md = [f"# Prior audit: `{pack_name}` pack", "",
          f"*Demo product `{pack.demo_product['label']}` at {pack.demo_product['price']} {pack.currency} per "
          f"{pack.period or 'period'}; share on the pack's template customers (base {base:.1%}); "
          f"{len(SEEDS)} seeds x {REPEATS} repeats; no language model.*", "",
          "## Where the priors come from", "",
          "- **Datasets (real, applied in full):** budget ranges are scaled by the country's income level (World "
          "Bank) and by the measured change in consumer prices from the starting year to the latest year (SingStat "
          "for Singapore, Eurostat for Europe, the US Bureau of Labor Statistics for the US). Other countries get "
          "the income scale only.",
          "- **Assumptions (everything else):** price sensitivity, feature weights, switching cost, risk, outside "
          "appeal, randomness, brand pull, incumbency and segment shares are the pack author's stated assumptions. "
          "No open dataset measures them. Surveys and articles about them are kept in the Resources library, as "
          "reference only, and never move a prior.", "",
          "## How much each prior class matters", "",
          "Each class's ranges, in every segment, multiplied by 0.75 and by 1.25. Change in the demo product's "
          "share, in percentage points.", "",
          "| Prior | What it is | x0.75 | x1.25 |", "|---|---|---|---|"]
    md += [f"| `{c}` | {MEANING[c]} | {lo * 100:+.1f} | {hi * 100:+.1f} |" for c, lo, hi in rows]
    md += ["", "## The biggest assumption: how well known the new product is", "",
           "The pack gives a brand-new product a brand score of 0 in every segment. If it were already known:", "",
           "| Brand score for the product | Change in share (points) |", "|---|---|"]
    md += [f"| {lv} | {d * 100:+.1f} |" for lv, d in known.items()]
    md += ["", "Read: no single prior class moves the share by more than about a point in either direction here, while "
           "giving the product a brand score of 0.4 moves it by several. The new product's lack of brand is the "
           "largest lever and an assumption the user should set for their own case.", "",
           "## Segments and ranges (the assumptions in full)", ""]
    for s in pack.segments:
        p = s.priors
        md += [f"### {s.name} (`{s.id}`, share {s.share:.0%}{', hostile' if s.hostile else ''})",
               f"- budget {p.budget}, price sensitivity {p.alpha}, switching {p.switch}, risk {p.risk}, "
               f"outside appeal {p.outside_utility}, randomness {p.tau}",
               f"- feature weights: {', '.join(f'{a} {r}' for a, r in p.w.items())}",
               f"- brand pull: {p.brand or 'none'}; starts with: {p.incumbent}",
               f"- basis: {s.evidence.replace('_', ' ')}", ""]
    return "\n".join(md)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="saas")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    text = audit(args.pack)
    (args.out / "prior_audit.md").write_text(text) if args.pack == "saas" else (
        args.out / f"prior_audit_{args.pack}.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
