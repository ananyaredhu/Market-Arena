"use client";
// OWNER: Person A. Screen 4: "Scenario compare". Real data from POST /scenarios/compare: the same customers and the
// same random seed run twice, with your price changed in Scenario B. All numbers and sentences are computed.
import { useCallback, useEffect, useState } from "react";

import DeltaCard from "@/components/compare/DeltaCard";
import FlipSummary from "@/components/compare/FlipSummary";
import ScenarioCard from "@/components/compare/ScenarioCard";
import ScenarioControls from "@/components/compare/ScenarioControls";
import ShareBars from "@/components/compare/ShareBars";
import TradeoffNote from "@/components/compare/TradeoffNote";
import AppHeader from "@/components/layout/AppHeader";
import PageShell from "@/components/layout/PageShell";
import { post } from "@/lib/api";
import type { Tone } from "@/lib/cx";
import type { CompareResponse } from "@/lib/types";

const signed = (x: number) => {
  const p = Math.round(x * 100);
  return p === 0 ? "0" : `${p > 0 ? "+" : "−"}${Math.abs(p)}`;
};

const FLIP_TONES: Tone[] = ["coral", "amber", "violet", "teal", "blue", "accent"];

function tradeoff(d: CompareResponse): string {
  const share = `Your share moves by ${signed(d.headline.delta_p50)} points`;
  const rev = d.revenue.change_pct;
  if (rev == null) return `${share}. There is no baseline revenue to compare against.`;
  const pct = Math.abs(Math.round(rev * 100));
  const move = pct === 0 ? "does not change" : `${rev > 0 ? "rises" : "falls"} by ${pct}%`;
  return (
    `${share}, and the simulated revenue index (median share × price × 100 customers) ${move}. ` +
    "The model cannot see your costs, so test the price for real before you commit."
  );
}

const fetchCompare = (price: string) =>
  post<CompareResponse>("/scenarios/compare", { changes: { you: { price: Number(price) } }, label_b: "Scenario B" });

const errorText = (e: unknown) => (e instanceof Error ? e.message : "The comparison could not run.");

export default function ComparePage() {
  const [price, setPrice] = useState("3");
  const [data, setData] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async (p: string) => {
    setBusy(true);
    setError(null);
    try {
      setData(await fetchCompare(p));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    // first load: plain fetch, state is set once the answer arrives
    fetchCompare("3").then(setData).catch((e) => setError(errorText(e)));
  }, []);

  const subtitle = data?.overrides_applied
    ? `Scenario lab · compare · ${data.overrides_applied} human adjustment(s) applied`
    : "Scenario lab · compare";
  const sym = data?.currency_symbol ?? "S$";

  return (
    <PageShell glow="compare" className="!gap-[26px]">
      <AppHeader active="compare" subtitle={subtitle} />
      <ScenarioControls symbol={sym} price={price} onPrice={setPrice} onRun={() => run(price)} busy={busy} error={error} />

      {!data ? (
        <p className="text-muted">{busy ? "Running both scenarios…" : "No comparison yet."}</p>
      ) : (
        <>
          <div className="flex flex-wrap items-stretch gap-5">
            <ScenarioCard
              tag={`Scenario A · ${data.scenarios.a.label.toLowerCase()}`}
              price={`${sym}${data.scenarios.a.you_price.toFixed(2)} / ${data.period}`}
              note="Your current strategy"
            />
            <div aria-hidden="true" className="flex items-center justify-center text-[28px] text-accent">→</div>
            <ScenarioCard
              tag={`${data.scenarios.b.label} · what if`}
              price={`${sym}${data.scenarios.b.you_price.toFixed(2)} / ${data.period}`}
              note={data.scenarios.b.summary.join(" · ") || "No change"}
              highlight
            />
            <DeltaCard
              value={`${signed(data.headline.delta_p50)} pts`}
              caption="your share, median of repeated runs"
              range={`range ${signed(data.headline.range_low)} to ${signed(data.headline.range_high)}`}
            />
          </div>

          <ShareBars a={data.a} b={data.b} />

          <div className="flex flex-wrap gap-5">
            <FlipSummary
              items={
                data.flip_summary_b.length
                  ? data.flip_summary_b.slice(0, 3).map((r, i) => ({
                      pct: `${Math.round(r.pct * 100)}%`,
                      tone: FLIP_TONES[i % FLIP_TONES.length],
                      text: r.text.replace(/^\d+% /, ""),
                    }))
                  : [{ pct: "0%", tone: "muted" as Tone, text: "of any segment flips to you under the standard price cut or feature boost." }]
              }
            />
            <TradeoffNote>{tradeoff(data)}</TradeoffNote>
          </div>
        </>
      )}
    </PageShell>
  );
}
