"""Run the evidence researcher LIVE and show everything it did.

    make search-up                                   # local SearXNG on http://localhost:8888 (needs Docker)
    python -m scripts.try_live_evidence              # SaaS pack, Singapore
    python -m scripts.try_live_evidence --pack cafe --geography SG
    python -m scripts.try_live_evidence --no-population   # skip the before/after population comparison

It uses a real search engine (SearXNG), a real LLM (the provider chain in .env) and the World Bank API, then saves the
snapshot to data/evidence/ and prints: the research trace, every VERIFIED finding with its quote and URL, everything
that was DROPPED and why, the country economics, and how the findings changed the segment budgets. SEARXNG_URL defaults
to http://localhost:8888 for this script, so .env does not have to be edited. Keys are read from .env, never printed.
"""
from __future__ import annotations

import argparse
import os

from backend.common.env import load_env
from backend.common.fixtures import load_fixture


def _product(pack_name: str, pack) -> dict:
    if pack_name == "saas":
        return load_fixture("product_profile_saas")
    demo = pack.demo_product or {}
    return {"name": demo.get("label", pack_name), "pack": pack_name, "price": demo.get("price"),
            "description": f"{demo.get('label', 'A product')} in the {pack.label or pack_name} category."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="saas")
    ap.add_argument("--geography", default="SG")
    ap.add_argument("--provider", default="groq", help="LLM provider chain, e.g. groq or groq+openrouter")
    ap.add_argument("--reuse", help="analyse a saved snapshot id instead of researching again")
    ap.add_argument("--no-population", action="store_true")
    args = ap.parse_args()

    load_env()
    os.environ.setdefault("SEARXNG_URL", "http://localhost:8888")
    os.environ["LLM_MODE"] = "live"
    os.environ["LLM_PROVIDER_ORDER"] = args.provider.replace("+", ",")

    # imports after the environment is set
    from backend.evidence import agent, store
    from backend.evidence.apply import apply_evidence
    from backend.population.packs import load_pack

    pack = load_pack(args.pack)
    product = _product(args.pack, pack)
    print(f"researching: pack={args.pack} geography={args.geography} search={os.environ['SEARXNG_URL']} "
          f"llm={os.environ['LLM_PROVIDER_ORDER']}")
    print("(paced for free-tier limits; this can take several minutes)\n")

    if args.reuse:
        snap = store.load(args.reuse)
        path = store.RUN_DIR / f"{snap.snapshot_id}.json"
    else:
        snap = agent.research(args.pack, args.geography, product, segments={s.id: s.name for s in pack.segments})
        path = store.save(snap)

    print(f"STATUS: {snap.status.upper()}   saved: {path.name}")
    if snap.fallback_reason:
        print(f"fallback reason: {snap.fallback_reason}")
    print(f"stats: {snap.stats}\n")

    print("TRACE")
    for s in snap.trace:
        print(f"  {s.n:>2} {s.action:<10} {s.detail[:70]:<70} -> {s.result[:90]}")

    if snap.economics:
        e = snap.economics
        print(f"\nECONOMICS (World Bank): {e.country} GDP/person PPP {e.gdp_pc_ppp:,.0f} ({e.year}) vs "
              f"{e.baseline_iso} {e.baseline_gdp_pc_ppp:,.0f} -> budget scale x{e.budget_scale}\n  {e.source_url}")

    print(f"\nVERIFIED FINDINGS ({len(snap.findings)})")
    for f in snap.findings:
        num = f"{f.value} {f.currency or ''} {f.unit or ''}".strip() if f.value is not None else ""
        print(f"  [{f.kind}] {f.subject or 'all'}: {f.claim}  {num}\n     quote: \"{f.quote[:160]}\"\n     {f.url}")
    print(f"\nTREND NOTES ({len(snap.trend_notes)})")
    for t in snap.trend_notes:
        print(f"  [{t.effect}] {t.note}\n     quote: \"{t.quote[:160]}\"\n     {t.url}")
    print(f"\nDROPPED ({len(snap.dropped)})  (the verifier kept these OUT)")
    for d in snap.dropped:
        print(f"  - {d.what[:90]}  <- {d.reason}")

    if args.no_population:
        return 0
    # The effect of the evidence ALONE: apply it straight to the pack's template priors (no LLM involved).
    res = apply_evidence(pack, snap)
    print("\nEFFECT OF THE EVIDENCE ON THE TEMPLATE PRIORS (deterministic, no LLM)")
    print(f"  {'segment':<18} {'budget range':<24} {'free-tool share (incumbent mix)'}")
    for before, after in zip(pack.segments, res.segments, strict=True):
        fb = before.priors.incumbent.get("free_tool", 0.0) / sum(before.priors.incumbent.values())
        fa = after.priors.incumbent.get("free_tool", 0.0) / sum(after.priors.incumbent.values())
        bb, ba = before.priors.budget, after.priors.budget
        print(f"  {before.id:<18} {f'{bb[0]:.2f}-{bb[1]:.2f} -> {ba[0]:.2f}-{ba[1]:.2f}':<24} {fb:.2f} -> {fa:.2f}")
    print("applied:")
    for line in res.applied:
        print("  +", line)
    print("skipped:", res.skipped or "none")
    print("advisory (shown, never applied):", len(res.advisory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
