"use client";
// OWNER: Person A. Screen 4 mockup: "Scenario compare". Data: POST /scenarios/compare -> {a, b} RunResults.
import { useEffect, useState } from "react";

import DeltaCard from "@/components/compare/DeltaCard";
import FlipSummary from "@/components/compare/FlipSummary";
import ScenarioCard from "@/components/compare/ScenarioCard";
import ShareBars from "@/components/compare/ShareBars";
import TradeoffNote from "@/components/compare/TradeoffNote";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { post } from "@/lib/api";
import { FLIP_SUMMARY, SCENARIO_A, SCENARIO_B, TRADEOFF_NOTE } from "@/lib/mock/compare";
import type { RunResult } from "@/lib/types";

const signed = (x: number) => {
  const p = Math.round(x * 100);
  return p === 0 ? "0" : `${p > 0 ? "+" : "−"}${Math.abs(p)}`;
};

export default function ComparePage() {
  const [pair, setPair] = useState<{ a: RunResult; b: RunResult } | null>(null);

  useEffect(() => {
    post<{ a: RunResult; b: RunResult }>("/scenarios/compare").then(setPair);
  }, []);

  if (!pair) {
    return (
      <PageShell glow="compare">
        <AppHeader active="compare" subtitle="Scenario lab · compare" />
        <p className="text-muted">Loading…</p>
      </PageShell>
    );
  }

  const { a, b } = pair;
  // Conservative interval: worst case is B's p10 minus A's p90, best case is B's p90 minus A's p10.
  const lo = b.totals.you.p10 - a.totals.you.p90;
  const hi = b.totals.you.p90 - a.totals.you.p10;

  return (
    <PageShell glow="compare" className="!gap-[26px]">
      <AppHeader active="compare" subtitle="Scenario lab · compare" disclaimer="Sample numbers · simulated outcome under stated assumptions" />

      <div className="flex flex-wrap items-stretch gap-5">
        <ScenarioCard {...SCENARIO_A} />
        <div aria-hidden="true" className="flex items-center justify-center text-[28px] text-accent">→</div>
        <ScenarioCard {...SCENARIO_B} highlight />
        <DeltaCard
          value={`${signed(b.totals.you.p50 - a.totals.you.p50)} pts`}
          caption="your share, median of repeated runs"
          range={`range ${signed(lo)} to ${signed(hi)}`}
        />
      </div>

      <ShareBars a={a} b={b} />

      <div className="flex flex-wrap gap-5">
        <FlipSummary items={FLIP_SUMMARY} />
        <TradeoffNote>{TRADEOFF_NOTE}</TradeoffNote>
      </div>
    </PageShell>
  );
}
