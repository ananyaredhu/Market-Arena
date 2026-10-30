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
from backend.intake.currency import bare_dollar, currency_of_country
from backend.intake.geography import detect_geography, normalise_geography

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
        return normalise_geography(value)


def project_data_dir() -> Path:
    """Return the configurable directory used for project JSON documents."""
    return Path(os.getenv("MARKET_ARENA_DATA_DIR", str(DEFAULT_DATA_DIR)))


def _pack_config(pack: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "packs" / f"{pack}.yaml"
    return yaml.safe_load(path.read_text())


def _first_sentence(idea: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", idea.strip(), maxsplit=1)[0]
    return sentence[:240]


def _title(text: str) -> str:
    """Capitalise words that are all lower case; leave a word that already has a capital (StudyFlow, AI, NUS) alone."""
    return " ".join(w if any(c.isupper() for c in w) else w.capitalize() for w in text.split())


def _product_name(idea: str, pack: str) -> str:
    first = _first_sentence(idea)
    match = re.match(r"(?:an?\s+)?(.{2,70}?)\s+(?:is|for|that|which|helps)\b", first, re.IGNORECASE)
    if match:
        name = match.group(1).split(",")[0].strip(" .,:;-'\"")
        if name:
            return _title(name)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9&'-]*", first)
    if words:
        return _title(" ".join(words[:5]))
    return f"New {pack.title()} product"


_SYMBOLS = {"S$": "SGD", "US$": "USD", "A$": "AUD", "C$": "CAD", "€": "EUR", "£": "GBP", "₹": "INR", "$": None}
_CODES = {"SGD", "USD", "EUR", "GBP", "INR", "AUD", "CAD"}
_WORDS = {"dollar": None, "dollars": None, "euro": "EUR", "euros": "EUR", "rupee": "INR", "rupees": "INR"}
_AMOUNT = r"(\d[\d,]*(?:\.\d{1,2})?)"
_SYMBOL = r"(S\$|US\$|A\$|C\$|\$|€|£|₹|SGD|USD|EUR|GBP|INR|AUD|CAD)"
_AFTER = r"(SGD|USD|EUR|GBP|INR|AUD|CAD|\$|€|£|₹|dollars?|euros?|rupees?)"
_PRICE_BEFORE = re.compile(r"(?<![A-Za-z0-9])" + _SYMBOL + r"\s*" + _AMOUNT + r"(?![\d])", re.IGNORECASE)
_PRICE_AFTER = re.compile(r"(?<![A-Za-z0-9.,$])" + _AMOUNT + r"\s*" + _AFTER + r"(?![A-Za-z])", re.IGNORECASE)


def _currency(token: str, default_currency: str, geography: str | None) -> str:
    """A code, symbol or word to a currency code. A bare dollar sign is the market's own dollar when it has one, US
    dollars when the market uses another currency, and the pack's currency when no market is known."""
    key = token.upper() if token.upper() in _CODES | {"S$", "US$", "A$", "C$"} else token.lower()
    if key in _CODES:
        return key
    named = _SYMBOLS.get(key, _WORDS.get(key))
    if named:
        return named
    return bare_dollar(geography) or default_currency


def _extract_price(idea: str, default_currency: str, geography: str | None = None) -> tuple[float, str] | None:
    """The first explicit price in the idea: a symbol before the amount ($9, S$9, €4.50), a symbol, code or word after
    it (3$, 9 USD, 9 dollars, 500 rupees). A number with no currency (9 students, 3 cups) is never a price."""
    found = [(m.start(), m.group(2), m.group(1)) for m in _PRICE_BEFORE.finditer(idea)]
    found += [(m.start(), m.group(1), m.group(2)) for m in _PRICE_AFTER.finditer(idea)]
    if not found:
        return None
    _, amount, token = min(found)
    value = float(amount.replace(",", ""))
    return (value, _currency(token, default_currency, geography)) if value > 0 else None


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


_PACK_WORDS = {
    "saas": ("app", "apps", "software", "saas", "platform", "subscription", "online", "website", "digital", "tool",
             "planner", "ai", "dashboard", "plugin", "chatbot", "api"),
    "cafe": ("cafe", "café", "coffee", "tea", "bakery", "kopitiam", "espresso", "latte", "lattes", "boba", "pastry",
             "pastries", "brunch", "roastery", "barista", "bistro", "bubble tea"),
}
_FREE_OFFER = ("free", "sample", "trial", "loyalty", "reward", "points", "discount", "introductory", "tasting")


def _mentions(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])", text) for w in words)


def _pack_fit_warning(idea: str, pack: str, label: str) -> str | None:
    """A warning, never a refusal: the pack decides the competitors and customers the simulation uses."""
    text = idea.lower()
    if _mentions(text, _PACK_WORDS[pack]):
        return None
    other = next((p for p in _PACK_WORDS if p != pack and _mentions(text, _PACK_WORDS[p])), None)
    if other:
        return (f"This idea reads like a {other} idea, but the {label} market was chosen, so the simulation would use "
                "that market's competitors and customers. Check the industry pack.")
    return (f"This idea does not clearly match the {label} market, so the simulation would use that market's "
            "competitors and customers. Check the industry pack before trusting the result.")


def build_product_profile(request: ProjectCreateRequest) -> ProductProfile:
    """Derive a deliberately modest profile without calling an LLM."""
    config = _pack_config(request.pack)
    text = request.idea.lower()
    stated = request.geography
    geography = stated or detect_geography(request.idea)
    price = _extract_price(request.idea, config["currency"], geography)
    customers = _customers(request.idea, request.pack)
    missing: list[str] = []
    fit = _pack_fit_warning(request.idea, request.pack, config.get("label", request.pack))
    if fit:
        missing.append(fit)
    if price is None:
        missing.append("What price will customers pay?")
    if not customers:
        missing.append("Who is the primary target customer?")
    if geography is None:
        missing.append("Which geography should the market represent? (Singapore is assumed.)")
    geography = geography or "SG"
    if request.pack == "saas" and not _mentions(text, ("trial", "free tier", "freemium")):
        missing.append("Is there a free tier or trial?")
    cafe_location_terms = ("location", "near", "neighbourhood", "neighborhood")
    if request.pack == "cafe" and not any(word in text for word in cafe_location_terms):
        missing.append("Where will the café be located?")
    if request.pack == "cafe" and not _mentions(text, _FREE_OFFER):
        missing.append("Is there a free sample, loyalty reward or introductory offer?")

    profile = ProductProfile(
        name=_product_name(request.idea, request.pack),
        description=_first_sentence(request.idea),
        pack=request.pack,
        price=price[0] if price else 0.0,
        # The founder's own currency if they wrote one, else their country's, else the pack's. Never converted.
        currency=price[1] if price else (currency_of_country(geography) or config["currency"]),
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
