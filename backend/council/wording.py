"""Optional, constrained LLM wording for the Council verdict.

The deterministic template is the source of truth. An LLM may only rephrase
it; the Moderator re-checks every number in the rewrite against the evidence
and falls back to the template on any mismatch. No shared LLM wrapper exists
yet, so the LLM is injected as a plain ``complete(prompt) -> str`` callable.
"""
from __future__ import annotations

import json
from typing import Callable, Protocol


class Wording(Protocol):
    name: str

    def rewrite_verdict(self, draft: str, facts: dict) -> str:
        ...


class TemplateWording:
    name = "template"

    def rewrite_verdict(self, draft: str, facts: dict) -> str:
        return draft


class CallableLLMWording:
    name = "llm"

    PROMPT = (
        "Rewrite the verdict below in at most two plain sentences for a startup founder.\n"
        "Rules: use only numbers that appear in FACTS, copied exactly; do not add new numbers, "
        "forecasts or claims about real customers; keep the phrase 'simulated'.\n"
        "FACTS: {facts}\nVERDICT: {draft}\nREWRITE:"
    )

    def __init__(self, complete: Callable[[str], str]):
        self._complete = complete

    def rewrite_verdict(self, draft: str, facts: dict) -> str:
        return self._complete(self.PROMPT.format(facts=json.dumps(facts, sort_keys=True), draft=draft)).strip()
