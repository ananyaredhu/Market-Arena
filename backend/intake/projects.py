"""Deterministic project intake and JSON-file persistence for the first vertical slice."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException
from pydantic import BaseModel, field_validator

from backend.common.contracts import ProductProfile

SUPPORTED_PACKS = frozenset({"saas", "cafe"})
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class ProjectCreateRequest(BaseModel):
    """Input accepted by the project route; this is not a shared contract."""

    idea: str
    pack: str
    geography: str | None = None

    @field_validator("idea")
    @classmethod
    def idea_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("idea must not be blank")
        return value

    @field_validator("pack")
    @classmethod
    def pack_must_be_supported(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in SUPPORTED_PACKS:
            choices = ", ".join(sorted(SUPPORTED_PACKS))
            raise ValueError(f"unsupported pack '{value}'; supported packs are: {choices}")
        return value

    @field_validator("geography")
    @classmethod
    def normalize_geography(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value or None


def project_data_dir() -> Path:
    """Return the configurable directory used for project JSON documents."""
    return Path(os.getenv("MARKET_ARENA_DATA_DIR", str(DEFAULT_DATA_DIR)))


def _pack_config(pack: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "packs" / f"{pack}.yaml"
    return yaml.safe_load(path.read_text())


def _first_sentence(idea: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", idea.strip(), maxsplit=1)[0]
    return sentence[:240]


def _product_name(idea: str, pack: str) -> str:
    first = _first_sentence(idea)
    match = re.match(r"(?:an?\s+)?(.{2,70}?)\s+(?:is|for|that|which|helps)\b", first, re.IGNORECASE)
    if match:
        return match.group(1).strip(" .,:;-'\"").title()
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&'-]*", first)
    if words:
        return " ".join(words[:5]).title()
    return f"New {pack.title()} product"


def _extract_price(idea: str, default_currency: str) -> tuple[float, str] | None:
    """Return a price only for an explicit, currency-qualified amount in the idea."""
    patterns = (
        r"\b(S\$|SGD\s*|US\$|USD\s*|\$)\s*(\d+(?:\.\d{1,2})?)\b",
        r"\b(\d+(?:\.\d{1,2})?)\s*(SGD|USD)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, idea, re.IGNORECASE)
        if not match:
            continue
        first_group = match.group(1).upper().replace(" ", "")
        if first_group.startswith(("S", "U", "$")):
            amount = float(match.group(2))
            currency_token = first_group
        else:
            amount = float(match.group(1))
            currency_token = match.group(2).upper()
        currency = "USD" if currency_token in {"US$", "USD"} else default_currency
        return amount, currency
    return None


def _customers(idea: str, pack: str) -> list[str]:
    text = idea.lower()
    candidates = (
        ("university students", ("student", "university", "exam")),
        ("small teams", ("team", "business", "startup")),
        ("remote workers", ("remote", "cowork", "work from cafe")),
        ("office workers", ("office", "lunch")),
        ("local residents", ("neighbourhood", "neighborhood", "local")),
    )
    found = [label for label, terms in candidates if any(term in text for term in terms)]
    if found:
        return found[:2]
    return ["local customers"] if pack == "cafe" else []


def _feature_strengths(idea: str, attributes: list[str]) -> dict[str, float]:
    text = idea.lower()
    keywords = {
        "ai_planning": ("ai", "plan", "schedule", "re-plan"),
        "simplicity": ("simple", "easy", "quick"),
        "privacy": ("private", "privacy", "secure"),
        "integrations": ("integrat", "calendar", "sync"),
        "taste_quality": ("coffee", "roast", "fresh", "taste"),
        "distance_minutes": ("near", "nearby", "walk", "location"),
        "wait_time": ("fast", "quick", "queue", "wait"),
        "ambience": ("ambience", "cozy", "work", "seating"),
        "dietary_fit": ("vegan", "halal", "dietary", "vegetarian"),
        "loyalty_perks": ("loyalty", "rewards", "points"),
    }
    return {
        attribute: 0.6 if any(term in text for term in keywords.get(attribute, ())) else 0.2
        for attribute in attributes
    }


def build_product_profile(request: ProjectCreateRequest) -> ProductProfile:
    """Derive a deliberately modest profile without calling an LLM."""
    config = _pack_config(request.pack)
    price = _extract_price(request.idea, config["currency"])
    customers = _customers(request.idea, request.pack)
    geography = request.geography or "SG"
    missing: list[str] = []
    if price is None:
        missing.append("What price will customers pay?")
    if not customers:
        missing.append("Who is the primary target customer?")
    if request.geography is None:
        missing.append("Which geography should the market represent? (Singapore is assumed.)")
    if request.pack == "saas" and not any(word in request.idea.lower() for word in ("trial", "free tier", "freemium")):
        missing.append("Is there a free tier or trial?")
    cafe_location_terms = ("location", "near", "neighbourhood", "neighborhood")
    if request.pack == "cafe" and not any(word in request.idea.lower() for word in cafe_location_terms):
        missing.append("Where will the café be located?")

    profile = ProductProfile(
        name=_product_name(request.idea, request.pack),
        description=_first_sentence(request.idea),
        pack=request.pack,
        price=price[0] if price else 0.0,
        currency=price[1] if price else config["currency"],
        target_customers=customers,
        features=_feature_strengths(request.idea, config["attributes"]),
        geography=geography,
        missing_assumptions=missing,
    )
    # Keep validation explicit at the boundary where generated data becomes persisted data.
    return ProductProfile.model_validate(profile.model_dump())


def _project_path(project_id: str, data_dir: Path | None = None) -> Path:
    return (data_dir or project_data_dir()) / f"{project_id}.json"


def create_persisted_project(request: ProjectCreateRequest) -> dict[str, Any]:
    profile = build_product_profile(request)
    data_dir = project_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    while True:
        project_id = f"proj_{uuid.uuid4().hex}"
        path = _project_path(project_id, data_dir)
        if not path.exists():
            break
    record = {
        "id": project_id,
        "idea": request.idea,
        "pack": request.pack,
        "geography": request.geography,
        "profile": profile.model_dump(),
        "competitors": [],
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True))
    temporary.replace(path)
    return {"id": project_id, "profile": profile.model_dump(), "competitors": []}


def get_persisted_project(project_id: str) -> dict[str, Any]:
    path = _project_path(project_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"project '{project_id}' was not found")
    record = json.loads(path.read_text())
    profile = ProductProfile.model_validate(record["profile"])
    return {"id": record["id"], "profile": profile.model_dump(), "competitors": record.get("competitors", [])}
