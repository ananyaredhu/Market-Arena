"""Run the population generator against REAL LLM providers, one at a time, and report what happened.

    python -m scripts.try_live_population                       # groq, openrouter, ollama
    python -m scripts.try_live_population --providers groq      # just one
    python -m scripts.try_live_population --pack cafe --n 150

For each provider it forces LLM_MODE=live with only that provider in the chain, bypasses the cache so a real
call is made, and prints: whether the LLM's proposal was accepted or replaced by the pack template (and why),
latency, token usage, and the segments produced. Keys come from .env and are never printed.
"""
from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

from backend.common import llm
from backend.common.env import load_env
from backend.common.fixtures import load_fixture


def run(provider: str, pack: str, n: int) -> dict:
    from backend.population.generator import generate_population  # import after env is loaded
    from backend.population.models import PopulationRequest

    os.environ["LLM_MODE"] = "live"
    os.environ["LLM_PROVIDER_ORDER"] = provider.replace("+", ",")  # "openrouter+groq" tests a fallback chain
    llm.CACHE_DIR = Path(tempfile.mkdtemp())  # fresh cache dir: force a real call
    llm._cooldown_until.clear()

    seen: list[dict] = []  # what the model actually returned, for diagnosis (no headers or keys)
    real = llm._http_transport

    def spy(p, messages, timeout):
        t = time.perf_counter()
        try:
            out = real(p, messages, timeout)
            seen.append({"ok": True, "secs": time.perf_counter() - t, "text": out["text"], "usage": out.get("usage")})
            return out
        except Exception as e:  # noqa: BLE001
            seen.append({"ok": False, "secs": time.perf_counter() - t, "error": f"{type(e).__name__}: {str(e)[:200]}"})
            raise

    llm._http_transport = spy
    t0 = time.perf_counter()
    try:
        product = load_fixture("product_profile_saas") if pack == "saas" else None  # the model needs the idea
        pop = generate_population(PopulationRequest(pack=pack, n_agents=n, seed=42, product=product))
        error = None
    except Exception as e:  # noqa: BLE001
        pop, error = None, f"{type(e).__name__}: {e}"
    finally:
        llm._http_transport = real
    return {"pop": pop, "error": error, "calls": seen, "secs": time.perf_counter() - t0}


def report(provider: str, r: dict) -> bool:
    print(f"\n=== {provider} " + "=" * (60 - len(provider)))
    calls = r["calls"]
    print(f"provider calls: {len(calls)} | total time {r['secs']:.1f}s")
    for i, c in enumerate(calls, 1):
        if c["ok"]:
            print(f"  call {i}: ok in {c['secs']:.1f}s, usage={c['usage']}")
        else:
            print(f"  call {i}: FAILED in {c['secs']:.1f}s -> {c['error']}")
    if r["error"]:
        print("generator raised:", r["error"])
        return False
    g = r["pop"]["generation"]
    print(f"result source: {g['source'].upper()}  | fallback_reason: {g['fallback_reason']}")
    if g["source"] == "template" and calls and calls[-1]["ok"]:
        print("  raw model answer (first 400 chars):", calls[-1]["text"][:400].replace("\n", " "))
    print("segments:")
    for s in r["pop"]["segments"]:
        n_seg = sum(1 for a in r["pop"]["agents"] if a["segment"] == s["id"])
        print(f"  {s['id']:<18} share {s['share']:.2f}  agents {n_seg:>3}  hostile={s.get('hostile')}  | {s['name']}")
    return g["source"] == "llm"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="groq,openrouter,ollama")
    ap.add_argument("--pack", default="saas")
    ap.add_argument("--n", type=int, default=150)
    args = ap.parse_args()

    loaded = load_env()
    print(f"loaded {len(loaded)} variable(s) from .env (names only): {', '.join(loaded) or 'none'}")
    results = {}
    for provider in [p.strip() for p in args.providers.split(",") if p.strip()]:
        results[provider] = report(provider, run(provider, args.pack, args.n))
    print("\nSUMMARY (True = the LLM's own segments were accepted):", results)
    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
