"""Population generator (Person A): propose segment priors, sample agents, validate, fall back if needed.

    generate_population(PopulationRequest) -> dict   (matches the shared `Population` contract)

Flow
  1. Load the pack template (hand-written priors, packs/<pack>.yaml).
  2. Ask the LLM for segment priors suited to this product and market (task "population_priors:<pack>").
     In LLM_MODE=mock the answer is the template itself, so everything works offline.
  3. Check the proposal's structure; sample agents numerically (seeded, no LLM); run the validators.
  4. If the LLM answer is malformed, unreachable or fails validation: use the template instead and record why.
  5. If even the template fails validation, raise PopulationError (the pack file needs fixing).

The evidence-first step (Master Plan 4.6) will adjust the proposal before step 3; it plugs in here later.
"""
from __future__ import annotations

import json
import os

from pydantic import ValidationError

from backend.common.contracts import Population
from backend.common.llm import LLMError, complete_json, register_mock
from backend.population.models import PackSpec, PopulationRequest, PriorsProposal
from backend.population.packs import available_packs, load_pack
from backend.population.sampler import sample_agents
from backend.population.validators import validate_population

CONTRACT_TAGS = {"evidence", "user_supplied", "llm_assumption"}

SYSTEM = (
    "You design customer segments for a market simulation. You do not predict sales and you must not be "
    "optimistic: include customers who will never buy. Reply with JSON only."
)


class PopulationError(RuntimeError):
    pass


def _template(pack: PackSpec) -> dict:
    return {"segments": [s.model_dump() for s in pack.segments]}


# Offline/mock mode: the "LLM" answer for a pack is the pack's own template priors.
for _name in available_packs():
    register_mock(f"population_priors:{_name}", lambda n=_name: _template(load_pack(n)))


def _prompt(req: PopulationRequest, pack: PackSpec, option_ids: list[str]) -> str:
    return (
        f"Product (from intake): {json.dumps(req.product or {'note': 'use the pack demo product'})}\n"
        f"Market: {req.geography}. Pack: {pack.label or pack.pack}. Currency: {pack.currency}.\n"
        f"Attribute keys (use exactly these in every segment's w): {pack.attributes}\n"
        f"Option ids allowed in brand and incumbent: {option_ids + [pack.outside_id]}\n"
        "Rules: 4 to 6 segments, shares sum to 1; at least one hostile segment (loyal to a free or incumbent "
        "alternative, high switching cost); budgets realistic for this market and not higher than the template; "
        "every parameter is a [low, high] range; incumbent is a weight per option id.\n"
        f"Template to adapt (keep its structure):\n{json.dumps(_template(pack))}"
    )


def _check_proposal(proposal: PriorsProposal, pack: PackSpec, option_ids: list[str]) -> PackSpec:
    """Return a PackSpec built from the proposal, or raise ValueError/ValidationError describing the problem."""
    allowed = set(option_ids) | {pack.outside_id}
    for s in proposal.segments:
        unknown = (set(s.priors.brand) | set(s.priors.incumbent)) - allowed
        if unknown:
            raise ValueError(f"segment '{s.id}' mentions unknown option ids {sorted(unknown)}")
    return PackSpec.model_validate({**pack.model_dump(), "segments": [s.model_dump() for s in proposal.segments]})


def _build(pack: PackSpec, spec: PackSpec, req: PopulationRequest, option_ids: list[str]) -> dict:
    agents = sample_agents(spec.segments, pack.attributes, option_ids, pack.outside_id, req.n_agents, req.seed)
    return {
        "population_id": f"pop_{pack.pack}_{req.seed}",
        "seed": req.seed,
        "pack": pack.pack,
        "attributes": pack.attributes,
        "geography": req.geography,
        "evidence_snapshot_id": None,
        "segments": [
            {
                "id": s.id,
                "name": s.name,
                "share": s.share,
                "hostile": s.hostile,
                # Template and LLM priors are both assumptions; the pack's own label is not a contract tag.
                "evidence": s.evidence if s.evidence in CONTRACT_TAGS else "llm_assumption",
            }
            for s in spec.segments
        ],
        "agents": agents,
    }


def generate_population(req: PopulationRequest | None = None) -> dict:
    req = req or PopulationRequest()
    pack = load_pack(req.pack)
    option_ids = ["you"] + [c["id"] for c in pack.competitors]

    source, reason, unchanged = "llm", None, False
    spec = pack
    try:
        proposal = complete_json(
            f"population_priors:{pack.pack}",
            _prompt(req, pack, option_ids),
            PriorsProposal,
            system=SYSTEM,
            # No `fallback=` here on purpose: complete_json would swallow the failure and we could not
            # record why the template was used. We catch LLMError below instead.
        )
        spec = _check_proposal(proposal, pack, option_ids)
        unchanged = [s.model_dump() for s in spec.segments] == [s.model_dump() for s in pack.segments]
        if unchanged and os.getenv("LLM_MODE", "mock") == "mock":
            source = "template"  # offline mode: the "answer" is the template itself
        # In live mode an unchanged answer is still the model's answer (small models often echo the
        # template back); it is reported as source "llm" with unchanged_from_template=True.
    except (LLMError, ValidationError, ValueError) as e:
        source, reason, spec = "template", f"proposal rejected: {str(e).splitlines()[0]}", pack

    population = _build(pack, spec, req, option_ids)
    issues = validate_population(population, pack)
    if issues and source != "template":
        source, reason = "template", "validation failed: " + "; ".join(str(i) for i in issues)
        population = _build(pack, pack, req, option_ids)
        issues = validate_population(population, pack)
    if issues:
        raise PopulationError(f"template priors for pack '{pack.pack}' fail validation: {[str(i) for i in issues]}")

    population["generation"] = {
        "source": source,
        "fallback_reason": reason,
        "unchanged_from_template": unchanged and source == "llm",
        "validation": "passed",
    }
    return Population.model_validate(population).model_dump(mode="json")
