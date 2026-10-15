"""Glass-Box narration (Person A): numbers first, language second, and every sentence is verified.

Flow
  1. Code computes the FINAL numbers (utility breakdown, flips, probability) and freezes them in `Facts`.
  2. Code writes a deterministic template sentence from the same facts (always available, always faithful).
  3. The LLM sees ONLY `Facts` and is asked to phrase them naturally. It never computes or decides anything.
  4. `verify()` checks the LLM's sentence against the facts: only numbers from the facts, only option names from
     the facts, only reasons that are in the facts, mentions the chosen option and the main driver, and stays short.
     It is wired in as a Pydantic validator, so complete_json's retry loop sends the model the exact problem.
  5. Anything that fails (provider down, rate limit, still failing after retries) falls back to the template.

In LLM_MODE=mock no call is made and the template is used.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError, field_validator

from backend.common.llm import LLMError, complete_json

PHRASE = {
    "price": "price",
    "feature": "features",
    "brand": "brand preference",
    "switch": "switching cost",
    "risk": "risk of a new product",
    "outside": "the appeal of doing nothing",
}
# Words that signal each reason. A reason may only be mentioned if it is in the facts.
LEXICON = {
    "price": ("price", "pricing", "cheap", "expensive", "afford"),  # not "cost": "switching cost" is its own reason
    "feature": ("feature", "functionality", "capabilit"),
    "brand": ("brand", "loyal", "familiar", "trust"),
    "switch": ("switch", "migrat", "inertia", "credit"),
    "risk": ("risk", "unproven", "untested"),
    "outside": ("nothing", "skip", "stay put"),
}
MAX_CHARS = 320
MAX_SENTENCES = 3
# A reason that counted AGAINST the choice may only be mentioned together with one of these.
CONTRAST = (
    "despite", "although", "even though", "though", "while", "but", "yet", "however", "outweigh", "beat",
    "against", "counted", "whereas", "rather than", "instead", "overcame", "not enough", "still",
)
REJECTIONS: list[str] = []  # diagnostics only: the most recent verifier problems (see scripts/try_live_narration.py)


@dataclass(frozen=True)
class Driver:
    term: str  # price | feature | brand | switch | risk
    delta: float  # component of the chosen option MINUS the runner-up's, rounded to 2 decimals


@dataclass(frozen=True)
class Facts:
    """Everything the narration may say. Already rounded exactly as it may be quoted."""

    chosen: str
    runner_up: str | None
    your_product: str
    option_labels: tuple[str, ...]
    drivers: tuple[Driver, ...]
    p_choice_pct: int | None = None
    against_odds: bool = False
    locked: bool = False
    money: str = "S$"
    already_top: bool = False  # the customer prefers your product
    price_drop: float | None = None
    price_rise: float | None = None
    feature_attr: str | None = None
    feature_amount: float | None = None
    switch_incentive: float | None = None
    price_unreachable: bool = False  # a price cut was considered and cannot flip this customer
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_levers(self) -> bool:
        levers = (self.price_drop, self.feature_amount, self.switch_incentive, self.price_rise)
        return any(x is not None for x in levers)

    def as_prompt_dict(self) -> dict:
        """What the LLM sees. Direction is spelled out (two lists, positive sizes) so a sign cannot be misread."""
        skip = ("option_labels", "notes", "drivers")
        d = {k: v for k, v in self.__dict__.items() if k not in skip and v not in (None, False)}
        by_size = sorted(self.drivers, key=lambda x: -abs(x.delta))
        d["reasons_for_choosing"] = [{"reason": PHRASE[x.term], "size": abs(x.delta)} for x in by_size if x.delta > 0]
        d["reasons_against_choosing"] = [
            {"reason": PHRASE[x.term], "size": abs(x.delta)} for x in by_size if x.delta < 0
        ]
        return d

    def allowed_numbers(self) -> list[float]:
        nums = [abs(d.delta) for d in self.drivers]
        for v in (self.price_drop, self.price_rise, self.feature_amount, self.switch_incentive, self.p_choice_pct):
            if v is not None:
                nums.append(float(v))
        return nums

    def allowed_concepts(self) -> set[str]:
        c = {d.term for d in self.drivers}
        if self.price_drop is not None or self.price_rise is not None or self.price_unreachable:
            c.add("price")
        if self.feature_amount is not None:
            c.add("feature")
        if self.switch_incentive is not None:
            c.add("switch")
        if not self.has_levers:  # "no price, feature or credit change would win this customer"
            c |= {"price", "feature", "switch"}
        return c


# ---------------------------------------------------------------- template (always faithful)
def _join(items: list[str], word: str = "and") -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" {word} " + items[-1]


def template_text(f: Facts) -> str:
    def fmt(d: Driver) -> str:
        return f"{PHRASE[d.term]} ({'+' if d.delta > 0 else '−'}{abs(d.delta):.2f})"

    pos = [fmt(d) for d in sorted(f.drivers, key=lambda d: -abs(d.delta)) if d.delta > 0]
    neg = [fmt(d) for d in sorted(f.drivers, key=lambda d: -abs(d.delta)) if d.delta < 0]
    base = f"Chose {f.chosen} over {f.runner_up}" if f.runner_up else f"Chose {f.chosen}"
    if pos and neg:
        s1 = f"{base} because {_join(pos)} outweighed {_join(neg)}."
    elif pos:
        s1 = f"{base} because of {_join(pos)}."
    elif neg:
        s1 = f"{base} even though {_join(neg)} counted against it."
    else:
        s1 = f"{base}."
    parts = [s1]
    if f.against_odds and f.p_choice_pct is not None:
        parts.append(f"The model gave this choice only {f.p_choice_pct}% likelihood, so it was an unlikely draw.")
    if f.locked:
        parts.append("This choice was set manually.")

    m = f.money
    if f.already_top:
        if f.price_rise is not None:
            limit = f"{m}{f.price_rise:.2f}"
            parts.append(f"{f.your_product} stays their top choice unless the price rises by more than {limit}.")
    else:
        levers = []
        if f.price_drop is not None:
            levers.append(f"a price cut of {m}{f.price_drop:.2f}")
        if f.feature_attr is not None and f.feature_amount is not None:
            levers.append(f"improving {f.feature_attr.replace('_', ' ')} by {f.feature_amount:.2f}")
        if f.switch_incentive is not None:
            levers.append(f"a switching credit worth {m}{f.switch_incentive:.2f}")
        if levers:
            parts.append(f"{_join(levers, 'or').capitalize()} would make {f.your_product} their top choice.")
        else:
            parts.append("No single price, feature or credit change would win this customer.")
    return " ".join(parts)


# ---------------------------------------------------------------- verifier
_NUM = re.compile(r"\d+(?:\.\d+)?")


def verify(text: str, f: Facts) -> list[str]:
    """Return the problems found (empty list = the sentence is faithful to the facts)."""
    problems: list[str] = []
    low = text.lower()
    if not text.strip():
        return ["the narration is empty"]
    if len(text) > MAX_CHARS:
        problems.append(f"too long ({len(text)} characters, max {MAX_CHARS})")
    if len(re.findall(r"[.!?](?:\s|$)", text)) > MAX_SENTENCES:
        problems.append(f"more than {MAX_SENTENCES} sentences")

    allowed = f.allowed_numbers()
    for tok in _NUM.findall(text):
        x = float(tok)
        if not any(abs(x - a) < 0.005 for a in allowed):
            problems.append(f"the number {tok} is not in the facts (allowed: {sorted(set(allowed))})")

    mentioned = {lbl for lbl in f.option_labels if lbl.lower() in low}
    allowed_labels = {f.chosen, f.your_product} | ({f.runner_up} if f.runner_up else set())
    for lbl in mentioned - allowed_labels:
        problems.append(f"mentions '{lbl}', which is not part of this decision")
    if f.chosen.lower() not in low:
        problems.append(f"does not name the chosen option '{f.chosen}'")

    ok = f.allowed_concepts()
    scrubbed = low  # option names are allowed even if they contain a reason-word (e.g. "Do nothing")
    for lbl in allowed_labels:
        scrubbed = scrubbed.replace(lbl.lower(), " ")
    for concept, words in LEXICON.items():
        if concept not in ok and any(w in scrubbed for w in words):
            problems.append(f"mentions a reason ({PHRASE[concept]}) that is not in the facts")
    # Direction: the sentence must explain the choice by the biggest reason FOR it (not merely the biggest number).
    pro = [d for d in f.drivers if d.delta > 0]
    pool = pro or list(f.drivers)  # no reason for the choice at all: fall back to the biggest number
    main = max(pool, key=lambda d: abs(d.delta)) if pool else None
    if main and not any(w in scrubbed for w in LEXICON[main.term]):
        problems.append(f"does not mention the main reason for the choice ({PHRASE[main.term]})")
    # A reason that counted against the choice must be framed as such (despite / even though / outweighed ...).
    against = [d for d in f.drivers if d.delta < 0]
    if any(any(w in scrubbed for w in LEXICON[d.term]) for d in against) and not any(c in low for c in CONTRAST):
        names = ", ".join(PHRASE[d.term] for d in against)
        problems.append(
            f"mentions a reason that counted AGAINST the choice ({names}) without saying so (use despite/even though)"
        )
    return problems


# ---------------------------------------------------------------- LLM phrasing
SYSTEM = (
    "You rewrite finished numbers as plain English for a founder. You do not analyse, estimate or add anything. "
    "Reply with JSON only."
)


def _prompt(f: Facts) -> str:
    return (
        "Facts about one simulated customer (final numbers, already computed):\n"
        f"{json.dumps(f.as_prompt_dict(), ensure_ascii=False)}\n\n"
        "Write 1 to 2 short sentences (under 45 words) explaining why this customer chose "
        f"'{f.chosen}'"
        + (f" over '{f.runner_up}'" if f.runner_up else "")
        + ". Rules: use ONLY these facts. Explain the choice by the biggest item in reasons_for_choosing. You may "
        "mention an item from reasons_against_choosing only as something that counted against the choice (say "
        "'despite' or 'even though'); never present it as a cause of the choice. If you quote a number, copy it "
        "exactly as given; do not add any other number, option name or reason; do not mention the simulation or "
        "the model.\n"
        'Return {"narration": "<text>"}.'
    )


def _model_for(f: Facts) -> type[BaseModel]:
    class Narration(BaseModel):
        narration: str

        @field_validator("narration")
        @classmethod
        def _faithful(cls, v: str) -> str:
            problems = verify(v, f)
            if problems:  # complete_json sends this message back to the model for another attempt
                REJECTIONS.append(f"{v!r} -> {'; '.join(problems)}")
                del REJECTIONS[:-20]
                raise ValueError("; ".join(problems))
            return v.strip()

    return Narration


def narrate(f: Facts) -> tuple[str, str]:
    """Return (text, source) where source is "llm" (verified) or "template"."""
    template = template_text(f)
    if os.getenv("LLM_MODE", "mock") == "mock":
        return template, "template"
    try:
        out = complete_json("narration", _prompt(f), _model_for(f), system=SYSTEM)
        return out.narration, "llm"
    except (LLMError, ValidationError, ValueError):
        return template, "template"
