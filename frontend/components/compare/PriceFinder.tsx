"use client";
// OWNER: Person A. "Find a price": runs the stored market at a series of prices (POST /pricing/suggest) and shows where to
// START testing a price for real. Real prices from the Resources library are listed as reference, never as an input.
import { useState } from "react";

import PriceCurve from "@/components/compare/PriceCurve";
import { Button, Card, SectionLabel } from "@/components/ui";
import { post } from "@/lib/api";
import { currentPriceNote, headline, parseCost } from "@/lib/price-finder";
import type { PriceSuggestResponse } from "@/lib/types";

export default function PriceFinder({
  projectId,
  runId,
  symbol,
  onUsePrice,
}: {
  projectId: string;
  runId: string | null;
  symbol: string;
  onUsePrice: (price: number) => void;
}) {
  const [cost, setCost] = useState("");
  const [data, setData] = useState<PriceSuggestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const parsed = parseCost(cost);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setData(await post<PriceSuggestResponse>("/pricing/suggest", { project_id: projectId, run_id: runId, cost: parsed.cost }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "The price search could not run.");
    } finally {
      setBusy(false);
    }
  }

  const sentence = data ? headline(data) : null;
  const where = data ? currentPriceNote(data) : null;
  return (
    <Card role="region" aria-label="Find a price" className="flex flex-col gap-4 !p-5">
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1.5">
          <SectionLabel>Find a price</SectionLabel>
          <p className="m-0 max-w-md text-xs leading-normal text-muted">
            Runs the same customers at about 14 prices and shows where your result peaks. Add what one sale costs you to
            look for profit instead of revenue.
          </p>
        </div>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs text-muted">Cost of one sale (optional)</span>
          <span className="flex items-center gap-2">
            <span className="font-mono text-ink-soft">{symbol}</span>
            <input
              aria-label="Cost of one sale"
              inputMode="decimal"
              value={cost}
              placeholder="none"
              onChange={(e) => setCost(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && parsed.ok && run()}
              className="min-h-11 w-28 rounded-lg border border-line-3 bg-bg px-3 font-mono text-ink"
            />
          </span>
        </label>
        <Button variant="primary" disabled={busy || !parsed.ok} onClick={run}>
          {busy ? "Searching…" : "Suggest a price"}
        </Button>
      </div>
      {!parsed.ok && <p role="alert" className="m-0 text-sm text-coral">The cost must be a number, zero or more.</p>}
      {error && <p role="alert" className="m-0 text-sm text-coral">{error}</p>}

      {data && (
        <div className="flex flex-col gap-4" aria-live="polite">
          {sentence ? (
            <div className="flex flex-wrap items-center gap-4">
              <p className="m-0 flex-1 text-base text-ink">
                {sentence} {where}
              </p>
              {data.suggestion && (
                <Button variant="secondary" onClick={() => onUsePrice(data.suggestion!.price)}>
                  Try {data.currency_symbol}
                  {data.suggestion.price.toFixed(2)} in Scenario B
                </Button>
              )}
            </div>
          ) : (
            <Card variant="warn">
              <p className="m-0 text-sm text-warn-ink">{data.notes[0]}</p>
            </Card>
          )}
          <PriceCurve data={data} />
          {data.suggestion && data.notes.length > 0 && (
            <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-xs text-muted">
              {data.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
          {data.reference_prices.length > 0 && (
            <Card variant="inset" className="flex flex-col gap-2">
              <SectionLabel>Real prices found (reference only)</SectionLabel>
              <p className="m-0 text-xs text-muted">{data.reference_note}</p>
              <ul className="m-0 flex list-none flex-col gap-1.5 p-0 text-sm text-ink-soft">
                {data.reference_prices.map((r) => (
                  <li key={r.url + r.quote}>
                    {r.claim}{" "}
                    <a href={r.url} target="_blank" rel="noreferrer" className="text-accent underline">
                      {r.domain}
                    </a>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}
    </Card>
  );
}
