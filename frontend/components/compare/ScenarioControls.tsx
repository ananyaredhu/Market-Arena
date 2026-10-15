"use client";
// OWNER: Person A. Inputs for Scenario B. The API also accepts feature and novelty changes and rival changes
// (POST /scenarios/compare {changes: {option_id: {price, features, novelty}}}); price is the one exposed here.
import { Button, Card, SectionLabel } from "@/components/ui";

export default function ScenarioControls({
  symbol,
  price,
  onPrice,
  onRun,
  busy,
  error,
}: {
  symbol: string;
  price: string;
  onPrice: (v: string) => void;
  onRun: () => void;
  busy: boolean;
  error: string | null;
}) {
  return (
    <Card variant="raised" className="flex flex-wrap items-end gap-4 !p-5">
      <label className="flex flex-col gap-1.5">
        <SectionLabel>Scenario B · your price</SectionLabel>
        <span className="flex items-center gap-2">
          <span className="font-mono text-ink-soft">{symbol}</span>
          <input
            aria-label="Scenario B price"
            inputMode="decimal"
            value={price}
            onChange={(e) => onPrice(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onRun()}
            className="min-h-11 w-28 rounded-lg border border-line-3 bg-bg px-3 font-mono text-ink"
          />
        </span>
      </label>
      <Button variant="primary" disabled={busy || price.trim() === "" || Number.isNaN(Number(price))} onClick={onRun}>
        {busy ? "Running…" : "Compare"}
      </Button>
      <p className="m-0 max-w-md text-xs leading-normal text-muted">
        Both scenarios use the same customers and the same random seed, so any difference comes from your change, not
        from chance.
      </p>
      {error && (
        <p role="alert" className="m-0 w-full text-sm text-coral">
          {error}
        </p>
      )}
    </Card>
  );
}
