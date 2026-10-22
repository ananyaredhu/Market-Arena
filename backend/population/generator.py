"""Population generator (Person A): propose segment priors, sample agents, validate, fall back if needed.

    generate_population(PopulationRequest) -> dict   (matches the shared `Population` contract)

Flow
  1. Load the pack template (hand-written priors, packs/<pack>.yaml).
  2. Ask the LLM for segment priors suited to this product and market (task "population_priors:<pack>").
     In LLM_MODE=mock the answer is the template itself, so everything works offline.
  3. Check the proposal's structure; sample agents numerically (seeded, no LLM); run the validators.
  4. If the LLM answer is malformed, unreachable or fails validation: use the template instead and record why.
  5. If even the template fails validation, raise PopulationError (the pack file needs fixing).

Evidence-first (Master Plan 4.6, opt-in with `research` or `evidence_snapshot_id`): after step 2 the verified
findings of the evidence researcher nudge the proposal inside fixed bands (backend/evidence/apply.py). If the result
fails validation, or the research found nothing, the proposal without evidence is used and the reason is recorded.
"""
from __future__ import annotations

import json
import os

from pydantic import ValidationError

from backend.common.contracts import Population
from backend.common.llm import LLMError, complete_json, register_mock
from backend.evidence import agent as evidence_agent
from backend.evidence import store as evidence_store
from backend.evidence.apply import apply_evidence
from backend.evidence.models import EvidenceSnapshot
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


def _build(pack: PackSpec, spec: PackSpec, req: PopulationRequest, option_ids: list[str],
           snapshot_id: str | None = None) -> dict:
    agents = sample_agents(spec.segments, pack.attributes, option_ids, pack.outside_id, req.n_agents, req.seed)
    return {
        "population_id": f"pop_{pack.pack}_{req.seed}",
        "seed": req.seed,
        "pack": pack.pack,
        "attributes": pack.attributes,
        "geography": req.geography,
        "evidence_snapshot_id": snapshot_id,
        "segments": [
            {
                "id": s.id,
                "name": s.name,
                "share": s.share,
                "hostile": s.hostile,
                # Template and LLM priors are both assumptions; the pack's own label is not a contract tag.
                "evidence": s.evidence if s.evidence in CONTRACT_TAGS else "llm_assumption",
                "sources": s.sources or None,
            }
            for s in spec.segments
        ],
        "agents": agents,
    }


def template_population(req: PopulationRequest) -> dict:
    """A validated population from the pack's own template priors: no LLM, no network, fully deterministic.
    The backtest uses this so its results cannot vary with a language model's answers."""
    pack = load_pack(req.pack)
    option_ids = ["you"] + [c["id"] for c in pack.competitors]
    population = _build(pack, pack, req, option_ids)
    issues = validate_population(population, pack)
    if issues:
        raise PopulationError(f"template priors for pack '{pack.pack}' fail validation: {[str(i) for i in issues]}")
    population["generation"] = {"source": "template", "fallback_reason": None, "unchanged_from_template": False,
                                "validation": "passed"}
    return Population.model_validate(population).model_dump(mode="json")


def _snapshot_for(req: PopulationRequest, pack: PackSpec) -> tuple[EvidenceSnapshot | None, str | None]:
    """(snapshot, note). A saved snapshot is reused by id; otherwise research runs if asked. Never raises."""
    if req.evidence_snapshot_id:
        try:
            return evidence_store.load(req.evidence_snapshot_id), None
        except (KeyError, ValueError):
            return None, f"evidence snapshot '{req.evidence_snapshot_id}' not found; original priors used"
    if req.research:
        snap = evidence_agent.research(pack.pack, req.geography, req.product,
                                       segments={x.id: x.name for x in pack.segments})
        try:
            evidence_store.save(snap)
        except OSError:
            pass  # not being able to save only means the snapshot cannot be reopened later
        return snap, snap.fallback_reason
    return None, None


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

    snap, evidence_note = _snapshot_for(req, pack)
    applied = apply_evidence(spec, snap, req.price_base_year)
    with_evidence = bool(applied.applied)
    if with_evidence and evidence_note:  # web research fell back, but a dataset adjustment still applied
        evidence_note = evidence_note.replace("original priors used", "dataset evidence still applied")
    if with_evidence:
        adjusted = PackSpec.model_validate(
            {**spec.model_dump(), "segments": [s.model_dump() for s in applied.segments]})
        population = _build(pack, adjusted, req, option_ids, snap.snapshot_id if snap else None)
        if validate_population(population, pack):
            with_evidence, evidence_note = False, "evidence-adjusted population failed validation; original priors used"
    if not with_evidence:
        population = _build(pack, spec, req, option_ids, snap.snapshot_id if snap and snap.status != "off" else None)
    issues = validate_population(population, pack)
    if issues and source != "template":
        source, reason = "template", "validation failed: " + "; ".join(str(i) for i in issues)
        population = _build(pack, pack, req, option_ids)
        with_evidence = False
        issues = validate_population(population, pack)
    if issues:
        raise PopulationError(f"template priors for pack '{pack.pack}' fail validation: {[str(i) for i in issues]}")

    population["generation"] = {
        "source": source,
        "fallback_reason": reason,
        "unchanged_from_template": unchanged and source == "llm",
        "validation": "passed",
    }
    if snap is not None or evidence_note:
        population["generation"]["evidence"] = {
            "status": snap.status if snap else "failed",
            "used": with_evidence,
            "note": evidence_note,
            "applied": applied.applied if with_evidence else [],
            "skipped": applied.skipped,
            "price_base_year": req.price_base_year,
            "reference_items": (len(snap.findings) + len(snap.trend_notes) + len(snap.datasets)) if snap else 0,
        }
    return Population.model_validate(population).model_dump(mode="json")
