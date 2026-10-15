"""Run Glass-Box narration against a REAL LLM for a batch of customers and report the verifier's verdicts.

    python -m scripts.try_live_narration                  # 12 customers on Groq
    python -m scripts.try_live_narration --provider openrouter --n 20

Prints, per customer, the verified sentence (or the template that replaced it), plus totals: how many sentences the
LLM got right first time, how many needed a retry, and how many fell back to the template. Keys come from .env.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="groq")
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()
    load_env()
    os.environ["LLM_MODE"] = "live"
    os.environ["LLM_PROVIDER_ORDER"] = args.provider
    llm.CACHE_DIR = Path(tempfile.mkdtemp())  # fresh cache: force real calls

    from backend.glassbox import narration  # import after env is set
    from backend.glassbox.explain import explain_agent

    run, pop, opts = load_fixture("run_result"), load_fixture("population_saas"), load_fixture("options_saas")
    calls: list[int] = []  # provider calls made per customer
    real = llm._http_transport
    counter = {"n": 0}

    def spy(p, messages, timeout):
        counter["n"] += 1
        return real(p, messages, timeout)

    llm._http_transport = spy
    tally = {"llm_first_try": 0, "llm_after_retry": 0, "template": 0}
    t0 = time.perf_counter()
    for a in pop["agents"][: args.n]:
        counter["n"] = 0
        e = explain_agent(run, pop, opts, a["id"])
        calls.append(counter["n"])
        if e["narration_source"] == "llm":
            tally["llm_first_try" if counter["n"] == 1 else "llm_after_retry"] += 1
        else:
            tally["template"] += 1
        print(f"\n{a['id']} [{e['narration_source']}, {counter['n']} call(s)]\n  {e['narration']}")
        print("  drivers:", [(d["term"], d["delta"]) for d in e["top_drivers"]])
        for why in narration.REJECTIONS:  # sentences the verifier rejected for this customer
            print("  rejected:", why[:230])
        narration.REJECTIONS.clear()
    print(f"\nTOTALS over {args.n} customers in {time.perf_counter() - t0:.0f}s: {tally}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
