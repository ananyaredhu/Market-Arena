"""Shared LLM wrapper (baseline; Person B owns and extends this file).

    complete_json(task, prompt, Model, system=None, fallback=None) -> Model instance

Modes (env LLM_MODE):
- mock (default): returns a fixture registered for `task`, no network, no keys needed.
- live: tries the provider chain in LLM_PROVIDER_ORDER (all OpenAI-compatible endpoints).

Live behaviour:
- Cache by hash of (task, system, prompt, schema name, provider order) in .cache/llm/.
- Per provider: up to 2 retries when the answer is not valid JSON for the schema; the validation
  error is sent back to the model.
- Transport failure (timeout, 429, 5xx) skips that provider for LLM_COOLDOWN seconds and moves on.
- If every provider fails: use `fallback()` (a deterministic template) if given, else LLMError.
- Token usage is appended to .cache/llm_usage.jsonl.

Free-tier models and limits change: VERIFY model names and limits before relying on them.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from backend.common.fixtures import load_fixture

T = TypeVar("T", bound=BaseModel)

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"
MAX_RETRIES = 2

# task -> fixture name, used in mock mode. Register more with register_mock().
_MOCKS: dict[str, str | Callable[[], dict]] = {
    "intake": "product_profile_saas",
    "agent_explain": "agent_explain",
    "council": "council",
    "kit": "kit",
}
_cooldown_until: dict[str, float] = {}


class LLMError(RuntimeError):
    pass


@dataclass
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str


# transport(provider, messages, timeout) -> {"text": str, "usage": {...}}; replaceable in tests
Transport = Callable[[Provider, list[dict], float], dict]


def register_mock(task: str, source: str | Callable[[], dict]) -> None:
    """Mock answer for a task: a fixture name or a zero-argument function returning a dict."""
    _MOCKS[task] = source


def _providers() -> list[Provider]:
    known = {
        "groq": Provider("groq", "https://api.groq.com/openai/v1",
                         os.getenv("GROQ_API_KEY", ""), os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")),
        "openrouter": Provider("openrouter", "https://openrouter.ai/api/v1",
                               os.getenv("OPENROUTER_API_KEY", ""),
                               os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")),
        "ollama": Provider("ollama", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                           "ollama", os.getenv("OLLAMA_MODEL", "qwen2.5:7b")),
    }
    order = os.getenv("LLM_PROVIDER_ORDER", "groq,openrouter,ollama").split(",")
    return [known[n.strip()] for n in order if n.strip() in known and known[n.strip()].api_key]


def _post(p: Provider, messages: list[dict], timeout: float, json_mode: bool) -> httpx.Response:
    payload: dict = {"model": p.model, "messages": messages, "temperature": 0.2}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return httpx.post(
        f"{p.base_url}/chat/completions", headers={"Authorization": f"Bearer {p.api_key}"}, json=payload,
        timeout=timeout,
    )


def _http_transport(p: Provider, messages: list[dict], timeout: float) -> dict:
    r = _post(p, messages, timeout, json_mode=True)
    if r.status_code == 400 and "json_validate_failed" in r.text:
        # The provider's own JSON check rejected the answer (reasoning models sometimes return nothing usable in
        # JSON mode). That is not an outage: ask once more without it. Our schema validation still applies.
        r = _post(p, messages, timeout, json_mode=False)
    r.raise_for_status()
    body = r.json()
    return {"text": body["choices"][0]["message"]["content"] or "", "usage": body.get("usage", {})}


def _extract_json(text: str) -> str:
    """The JSON object inside a reply, tolerating markdown fences or a sentence around it."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0].strip()
    i, j = s.find("{"), s.rfind("}")
    return s[i : j + 1] if i != -1 and j > i else s


def _cache_path(key: str) -> Path:
    return CACHE_DIR / "llm" / f"{key}.json"


def _log_usage(provider: Provider, task: str, usage: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    with (CACHE_DIR / "llm_usage.jsonl").open("a") as f:
        f.write(json.dumps({"t": time.time(), "task": task, "provider": provider.name,
                            "model": provider.model, "usage": usage}) + "\n")


def complete_json(
    task: str,
    prompt: str,
    model: type[T],
    *,
    system: str | None = None,
    fallback: Callable[[], dict] | None = None,
    transport: Transport | None = None,
) -> T:
    if os.getenv("LLM_MODE", "mock") == "mock":
        src = _MOCKS.get(task)
        if src is None:
            raise LLMError(f"no mock registered for task '{task}' (use register_mock)")
        return model.model_validate(load_fixture(src) if isinstance(src, str) else src())

    transport = transport or _http_transport
    providers = _providers()
    key = hashlib.sha256(json.dumps(
        [task, system, prompt, model.__name__, [p.name for p in providers]]).encode()).hexdigest()
    cached = _cache_path(key)
    if cached.exists():
        return model.model_validate_json(cached.read_text())

    timeout = float(os.getenv("LLM_TIMEOUT", "30"))
    cooldown = float(os.getenv("LLM_COOLDOWN", "60"))
    schema = json.dumps(model.model_json_schema())
    base = [{"role": "system", "content": (system or "") + f"\nReply with JSON matching: {schema}"},
            {"role": "user", "content": prompt}]

    for p in providers:
        if _cooldown_until.get(p.name, 0) > time.time():
            continue
        messages = list(base)
        for _attempt in range(MAX_RETRIES + 1):
            try:
                out = transport(p, messages, timeout)
            except Exception:  # timeout, 429, 5xx, connection error: skip this provider for a while
                _cooldown_until[p.name] = time.time() + cooldown
                break
            _log_usage(p, task, out.get("usage", {}))
            try:
                result = model.model_validate_json(_extract_json(out["text"]))
            except ValidationError as e:
                messages = base + [{"role": "assistant", "content": out["text"]},
                                   {"role": "user", "content": f"Invalid: {e}. Return corrected JSON only."}]
                continue
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(result.model_dump_json())
            return result

    if fallback is not None:
        return model.model_validate(fallback())
    raise LLMError(f"all providers failed for task '{task}'")
