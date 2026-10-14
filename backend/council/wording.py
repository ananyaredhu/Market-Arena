"""Optional, constrained LLM wording for the Council verdict.

The deterministic template is the source of truth. An LLM may only rephrase
it; the Moderator re-checks every number in the rewrite against the evidence
and falls back to the template on any mismatch. Live mode uses the shared
``complete_json`` wrapper. Mock mode stays on the template so a fixture verdict
cannot replace calculated numbers.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Protocol

from pydantic import BaseModel


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


class _VerdictRewrite(BaseModel):
    verdict: str


class SharedLLMWording:
    """Rephrase via ``backend.common.llm.complete_json``. Fallback is the template draft."""

    name = "llm"

    def rewrite_verdict(self, draft: str, facts: dict) -> str:
        from backend.common.llm import complete_json

        prompt = CallableLLMWording.PROMPT.format(facts=json.dumps(facts, sort_keys=True, default=str), draft=draft)

        def fallback() -> dict:
            return {"verdict": draft}

        return complete_json("council_verdict", prompt, _VerdictRewrite, fallback=fallback).verdict.strip()


def wording_from_env() -> Wording:
    """Mock and unset modes never call a provider. Live mode may, and falls back to the draft."""
    if os.getenv("LLM_MODE", "mock") != "live":
        return TemplateWording()
    return SharedLLMWording()
