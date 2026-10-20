"""Measure how faithful the Glass-Box sentences are, with a REAL LLM, and write a report.

    python -m scripts.eval_glassbox_faithfulness                      # 36 customers on Groq
    python -m scripts.eval_glassbox_faithfulness --n 60 --delay 4
    python -m scripts.eval_glassbox_faithfulness --offline            # template only, no network

What is measured (Master Plan 13.1: "cited drivers match the true top contributors, target >= 95%"):
  * DELIVERED faithfulness: of the sentences the user actually sees (LLM-written if it passed the verifier,
    otherwise the template), what share pass the independent audit? This is the number the product promises.
  * FIRST-ATTEMPT faithfulness: of the LLM's very first answers, before the verifier could reject or retry them,
    what share were already faithful? This shows how much the verifier matters.
  * Accepted-first-try / after-retry / template-fallback counts, and any "gate escapes" (verifier accepted a
    sentence that the audit then failed).
The audit (backend/glassbox/audit.py) is separate code that checks against the engine's UNROUNDED numbers.
Writes docs/eval/glassbox_faithfulness.md and .json. Keys come from .env and are never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from backend.common import llm
from backend.common.env import load_env
from backend.common.fixtures import load_fixture
from backend.common.stats import pct, wilson_interval

OUT = Path(__file__).resolve().parents[1] / "docs" / "eval"
RUNS = (("run_result", None), ("run_result_price3", 3.0))  # (fixture run, your price override)


def build_items(n: int, seed: int) -> list[dict]:
    """Stratified, deterministic sample: spread across scenarios and across what the customer chose."""
    pop, base_opts = load_fixture("population_saas"), load_fixture("options_saas")
    pools: dict[tuple[str, str], list[dict]] = {}
    for run_name, price in RUNS:
        run = load_fixture(run_name)
        opts = [dict(o) for o in base_opts]
        if price is not None:
            opts[0]["price"] = price
        for c in run["choices"]:
            item = {"run_name": run_name, "run": run, "opts": opts, "pop": pop,
                    "agent_id": c["agent_id"], "choice": c["choice"]}
            pools.setdefault((run_name, c["choice"]), []).append(item)
    rng = random.Random(seed)
    for pool in pools.values():
        rng.shuffle(pool)
    keys = sorted(pools)
    items: list[dict] = []
    while len(items) < n and any(pools.values()):
        for k in keys:
            if pools[k] and len(items) < n:
                items.append(pools[k].pop())
    return items


def unique_items(n: int, seed: int) -> list[dict]:
    """The sample, with customers whose facts are identical to an earlier one removed: the same customer appears in
    both scenarios, and identical facts would be answered from the cache and would not be independent evidence."""
    from backend.glassbox.explain import gather_facts

    seen: set[str] = set()
    out: list[dict] = []
    for item in build_items(n * 4, seed):
        g = gather_facts(item["run"], item["pop"], item["opts"], item["agent_id"])
        key = json.dumps(g.facts.as_prompt_dict(), sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) == n:
            break
    return out


def run_item(item: dict, attempts: int, retry_wait: float) -> dict:
    from backend.glassbox.audit import audit
    from backend.glassbox.explain import gather_facts
    from backend.glassbox.narration import narrate, template_text, verify

    g = gather_facts(item["run"], item["pop"], item["opts"], item["agent_id"])
    out = {"run": item["run_name"], "agent_id": item["agent_id"], "chosen": g.facts.chosen,
           "template": template_text(g.facts)}
    for attempt in range(attempts):
        seen: list[dict] = []
        real = llm._http_transport

        def spy(p, messages, timeout, _real=real, _seen=seen):
            t = time.perf_counter()
            try:
                o = _real(p, messages, timeout)
                _seen.append({"ok": True, "secs": time.perf_counter() - t, "text": o["text"]})
                return o
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e)[:120]}"
                _seen.append({"ok": False, "secs": time.perf_counter() - t, "error": err})
                raise

        llm._http_transport = spy
        try:
            text, source = narrate(g.facts)
        finally:
            llm._http_transport = real
        answered = [s for s in seen if s["ok"]]
        # Retry only when a call was actually attempted and failed (most likely a rate limit). In offline mode no
        # call is ever made, so there is nothing to retry.
        if answered or not seen or attempt == attempts - 1:
            break
        time.sleep(retry_wait)

    offline = os.environ.get("LLM_MODE") == "mock"  # template-only run: every customer counts as "answered"
    cache_hit = not seen and source == "llm"  # an earlier identical answer was reused: still the LLM's answer
    out.update(calls=len(seen), call_errors=[s["error"] for s in seen if not s["ok"]], final_text=text,
               final_source=source, final_audit=list(audit(text, g).failures),
               llm_answered=bool(answered) or offline or cache_hit)
    first = None
    if answered:
        try:
            first = json.loads(answered[0]["text"]).get("narration")
        except (ValueError, AttributeError):
            first = None
        out["first_attempt_text"] = first
        out["first_attempt_valid_json"] = first is not None
        if first is not None:
            out["first_attempt_audit"] = list(audit(first, g).failures)
            out["first_attempt_verifier"] = verify(first, g.facts)
    return out


def summarise(results: list[dict]) -> dict:
    answered = [r for r in results if r["llm_answered"]]
    delivered_ok = sum(1 for r in results if not r["final_audit"])  # everything a user would have seen
    llm_delivered = [r for r in results if r["final_source"] == "llm"]
    first_valid = [r for r in answered if r.get("first_attempt_valid_json")]
    first_ok = sum(1 for r in first_valid if not r["first_attempt_audit"])
    checks = Counter(c for r in first_valid for c in r["first_attempt_audit"])
    escapes = [r for r in answered if r["final_source"] == "llm" and r["final_audit"]]
    return {
        "customers": len(results),
        "llm_answered": len(answered),
        "llm_unavailable": len(results) - len(answered),
        "delivered_faithful": delivered_ok,
        "llm_delivered": len(llm_delivered),
        "llm_delivered_faithful": sum(1 for r in llm_delivered if not r["final_audit"]),
        "first_attempt_valid_json": len(first_valid),
        "first_attempt_faithful": first_ok,
        "first_attempt_failed_checks": dict(checks),
        "accepted_first_try": sum(1 for r in answered if r["final_source"] == "llm" and r["calls"] == 1),
        "accepted_after_retry": sum(1 for r in answered if r["final_source"] == "llm" and r["calls"] > 1),
        "fell_back_to_template": sum(1 for r in answered if r["final_source"] == "template"),
        "gate_escapes": [(r["agent_id"], r["final_audit"]) for r in escapes],
    }


def line(label: str, k: int, n: int, target: float | None = None) -> str:
    lo, hi = wilson_interval(k, n)
    mark = "" if target is None else ("  **meets target**" if k / n >= target else "  **below target**") if n else ""
    return f"| {label} | {k} / {n} | {pct(k / n) if n else 'n/a'} | {pct(lo)} to {pct(hi)} |{mark} |"


def write_report(meta: dict, s: dict, results: list[dict], offline: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "glassbox_faithfulness.json").write_text(json.dumps({"meta": meta, "summary": s, "offline_template": offline,
                                                                "results": results}, indent=2, default=str))
    n = s["llm_answered"]
    md = [
        "# Glass-Box faithfulness report", "",
        f"*Generated {meta['when']} · provider chain `{meta['provider']}` · model `{meta['model']}` · "
        f"{s['customers']} customers sampled (seed {meta['seed']}) from the 80-customer SaaS fixture, "
        "two scenarios (S$7 and S$3).*", "",
        "**What is measured.** The Glass-Box explanation for each customer is built in four steps: code computes the "
        "numbers, the LLM only rephrases them, a verifier gates the sentence in real time, and a template replaces it "
        "if it fails. An *independent audit* (separate code, checked against the engine's unrounded numbers) then "
        "tests every sentence for: only real numbers, only real reasons, the main reason named, reasons that counted "
        "against the choice framed as such, only options that are part of the decision, no false \"what would win "
        "you\" claim for a customer who already chose you, and length.", "",
        "| Measure | Passed | Rate | 95% interval | |", "|---|---|---|---|---|",
        line("**Delivered sentences faithful** (everything a user would see, LLM or template)",
             s["delivered_faithful"], s["customers"], 0.95),
        line("...of which written by the LLM", s["llm_delivered_faithful"], s["llm_delivered"], 0.95),
        line("LLM first answers faithful (before the verifier could reject or retry them)",
             s["first_attempt_faithful"], s["first_attempt_valid_json"]),
        line("Template sentences faithful (no LLM, all customers)", offline["faithful"], offline["total"], 0.95), "",
        f"Customers where the LLM answered: {n} of {s['customers']} "
        f"({s['llm_unavailable']} skipped because the provider was unavailable or rate-limited; they are not counted "
        "as faithful or unfaithful).", "",
        "## How the delivered sentences were produced", "",
        "| Outcome | Customers |", "|---|---|",
        f"| LLM sentence accepted on the first try | {s['accepted_first_try']} |",
        f"| LLM sentence accepted after the verifier sent it back | {s['accepted_after_retry']} |",
        f"| Verifier rejected the LLM; template shown instead | {s['fell_back_to_template']} |", "",
        f"**Gate escapes** (the verifier accepted a sentence the audit then failed): {len(s['gate_escapes'])}"
        + (f" {s['gate_escapes']}" if s["gate_escapes"] else ""), "",
        "## What the LLM got wrong on its first try", "",
    ]
    if s["first_attempt_failed_checks"]:
        md += ["| Check | First answers that failed it |", "|---|---|"]
        md += [f"| {k} | {v} |" for k, v in sorted(s["first_attempt_failed_checks"].items(), key=lambda kv: -kv[1])]
    else:
        md.append("No first answer failed any check in this sample.")
    bad = [r for r in results if r.get("first_attempt_audit")]
    if bad:
        md += ["", "Examples (the sentence, then what the audit objected to):", ""]
        md += [f"- `{r['agent_id']}` {r['first_attempt_audit']}: \"{r['first_attempt_text']}\"" for r in bad[:6]]
    md += ["", "## Sample of sentences delivered to users", ""]
    md += [f"- `{r['agent_id']}` ({r['final_source']}): {r['final_text']}" for r in results[:8]]
    md += ["", "## What running this evaluation changed", "",
           "Measuring found real problems, each fixed and covered by a test:", "",
           "- The template (the fallback) broke its own three-sentence rule for a customer who was both pinned and an "
           "unlikely draw. Fixed by merging two notes into one sentence.",
           "- A real number attached to the *wrong reason* (for example the switching-cost size next to \"features\") "
           "passed a plain \"is this number in the facts?\" check. Added a number-to-reason binding check to the gate "
           "and the audit.",
           "- Two reasons within 0.001 of each other were treated as a \"biggest\" and a \"second\", so a correct "
           "sentence naming either was rejected. Reasons within 10% of the biggest now tie for main reason.",
           "- The evaluation itself double-counted the same customer across two scenarios (identical facts, served "
           "from cache) and mislabelled cache hits as provider outages. Fixed.", "",
           "## Limits", "",
           "- The audit checks numbers, named reasons, direction and options. It cannot judge every nuance of wording "
           "(for example whether \"most compelling\" is an apt phrase).",
           f"- {s['customers']} customers is a small sample; read the interval, not just the percentage.",
           "- Customers come from one fixture population in one product category.",
           "- The audit and the verifier share a vocabulary of reason words, so both can miss an unusual synonym.", ""]
    (OUT / "glassbox_faithfulness.md").write_text("\n".join(md))


def offline_template_audit() -> dict:
    from backend.glassbox.audit import audit
    from backend.glassbox.explain import gather_facts
    from backend.glassbox.narration import template_text

    pop, base = load_fixture("population_saas"), load_fixture("options_saas")
    total = ok = 0
    for run_name, price in RUNS:
        run, opts = load_fixture(run_name), [dict(o) for o in base]
        if price is not None:
            opts[0]["price"] = price
        for c in run["choices"]:
            g = gather_facts(run, pop, opts, c["agent_id"])
            total += 1
            ok += audit(template_text(g.facts), g).faithful
    return {"total": total, "faithful": ok}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="groq")
    ap.add_argument("--n", type=int, default=36)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between customers (free-tier rate limits)")
    ap.add_argument("--attempts", type=int, default=2, help="tries per customer if the provider does not answer")
    ap.add_argument("--offline", action="store_true", help="template only, no LLM")
    args = ap.parse_args()

    load_env()
    os.environ["LLM_MODE"] = "mock" if args.offline else "live"
    os.environ["LLM_PROVIDER_ORDER"] = args.provider.replace("+", ",")
    os.environ["LLM_COOLDOWN"] = "1"  # a failing provider must not be skipped for 60s mid-evaluation
    llm.CACHE_DIR = Path(tempfile.mkdtemp())  # fresh cache: force real calls

    items = unique_items(args.n, args.seed)
    results = []
    for i, item in enumerate(items, 1):
        r = run_item(item, args.attempts, retry_wait=20.0)
        results.append(r)
        print(f"[{i:>3}/{len(items)}] {r['agent_id']} {r['final_source']:<8} calls={r['calls']} "
              f"final_audit={r['final_audit'] or 'ok'} first={r.get('first_attempt_audit', '-') or 'ok'}", flush=True)
        if not args.offline:
            time.sleep(args.delay)

    s = summarise(results)
    model = os.getenv("GROQ_MODEL", "") if args.provider.startswith("groq") else os.getenv("OPENROUTER_MODEL", "")
    meta = {"when": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"), "provider": args.provider, "model": model,
            "seed": args.seed, "n": args.n, "offline": args.offline}
    write_report(meta, s, results, offline_template_audit())
    print("\nSUMMARY", json.dumps({k: v for k, v in s.items() if k != "gate_escapes"}))
    print("gate escapes:", s["gate_escapes"] or "none")
    print(f"report: {OUT / 'glassbox_faithfulness.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
