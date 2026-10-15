"use client";
// OWNER: Person A. MOCKUP of the Glass-Box inspector (layout and styling from the design board).
// Frozen props: <GlassBoxDrawer agentId={string} runId={string} onOverride={() => void} />
// Data: GET /runs/{runId}/agents/{agentId} -> AgentExplain. Parts the contract does not carry yet
// (budget, incumbent, switching appetite, gap) are left out; add them as optional contract fields.
import { useEffect, useState } from "react";

import { Button, DivergingBar, SectionLabel } from "@/components/ui";
import { api } from "@/lib/api";
import { optionStyle, segmentStyle } from "@/lib/theme";
import type { AgentExplain } from "@/lib/types";

interface Props {
  agentId: string;
  runId: string;
  onOverride: () => void;
}

const TERM_LABEL: Record<string, string> = {
  price: "Price",
  feature: "Features",
  brand: "Brand",
  switch: "Switching",
  risk: "Risk",
  outside: "Doing nothing",
};

// Where the sentence came from, shown under it so the founder knows how much to trust the wording.
const SOURCE_NOTE: Record<string, string> = {
  llm: "Wording by AI from the numbers below, checked against them.",
  template: "Built directly from the numbers below.",
};

export default function GlassBoxDrawer({ agentId, runId, onOverride }: Props) {
  // Result is keyed by the request so switching agents shows "Loading" without resetting state in the effect.
  const key = `${runId}/${agentId}`;
  const [result, setResult] = useState<{ key: string; data?: AgentExplain; error?: string } | null>(null);

  useEffect(() => {
    api<AgentExplain>(`/runs/${runId}/agents/${agentId}`)
      .then((data) => setResult({ key, data }))
      .catch((e) => setResult({ key, error: String(e) }));
  }, [agentId, runId, key]);

  const current = result?.key === key ? result : null;
  if (current?.error) return <Panel><p className="text-coral">{current.error}</p></Panel>;
  const data = current?.data;
  if (!data) return <Panel><p className="text-muted">Loading…</p></Panel>;

  const seg = segmentStyle(data.segment);
  const chosen = optionStyle(data.choice);
  const runnerUp = data.runner_up ? optionStyle(data.runner_up) : null;
  const maxAbs = Math.max(0.01, ...data.top_drivers.map((d) => Math.abs(d.delta)));
  const flip = data.flip;

  return (
    <Panel>
      <div className="flex items-center justify-between">
        <SectionLabel>Glass-Box · agent {data.agent_id}</SectionLabel>
      </div>

      <div className="flex items-center gap-3.5">
        <div
          className="h-12 w-12 shrink-0 rounded-full"
          style={{ background: seg.color, boxShadow: "0 0 0 4px rgba(255,255,255,0.2)" }}
        />
        <div>
          <div className="font-display text-[22px] font-bold">{seg.label}</div>
          <div className="text-[13px] text-muted">Chose {chosen.label}</div>
        </div>
      </div>

      <div>
        <p className="m-0 text-base leading-normal">{data.narration}</p>
        {data.narration_source && SOURCE_NOTE[data.narration_source] && (
          <p className="m-0 mt-1.5 text-xs text-muted">{SOURCE_NOTE[data.narration_source]}</p>
        )}
      </div>

      <div>
        <div className="mb-2 flex justify-between text-xs text-muted">
          <span>← favours {runnerUp?.label ?? "runner-up"}</span>
          <span>favours {chosen.label} →</span>
        </div>
        <div className="flex flex-col gap-2.5">
          {data.top_drivers.map((d) => (
            // Positive delta favours the chosen option (right); negative favours the runner-up (left).
            <DivergingBar
              key={d.term}
              label={TERM_LABEL[d.term] ?? d.term}
              value={d.delta / maxAbs}
              display={`${d.delta >= 0 ? "+" : "−"}${Math.abs(d.delta).toFixed(2)}`}
            />
          ))}
        </div>
      </div>

      <div className="rounded-[14px] border border-line-2 bg-surface-3 p-4">
        <SectionLabel tone="accent" className="mb-2.5">What would flip me</SectionLabel>
        <div className="flex gap-2.5">
          {flip?.price_rise != null ? (
            // Customers who already prefer you: how far the price can rise before they leave.
            <FlipTile value={`+S$${flip.price_rise.toFixed(2)}`} caption="price rise before they leave" />
          ) : (
            <FlipTile
              value={flip?.price_drop != null ? `−S$${flip.price_drop.toFixed(2)}` : "n/a"}
              caption="price drop"
            />
          )}
          <FlipTile
            value={flip?.feature_boost ? `+${flip.feature_boost.amount.toFixed(2)}` : "n/a"}
            caption={flip?.feature_boost ? `${flip.feature_boost.attr.replace("_", " ")} strength` : "feature boost"}
          />
        </div>
        {flip?.switch_incentive != null && (
          <p className="mt-2.5 text-xs leading-normal text-ink-soft">
            Or a switching credit worth S${flip.switch_incentive.toFixed(2)}.
          </p>
        )}
        {flip?.note && <p className="mt-2.5 text-xs leading-normal text-muted">{flip.note}</p>}
      </div>

      <div className="flex flex-wrap gap-2">
        {["Lock choice", "Edit parameters", "Exclude"].map((label) => (
          <Button key={label} onClick={onOverride} className="px-4">
            {label}
          </Button>
        ))}
      </div>
      <p className="text-xs leading-normal text-muted">
        Every override is written to the audit trail: machine-generated vs. human-adjusted.
      </p>
    </Panel>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <aside className="flex h-full w-full flex-col gap-5 border-l border-line bg-[#0f1420] p-6">{children}</aside>
  );
}

function FlipTile({ value, caption }: { value: string; caption: string }) {
  return (
    <div className="flex-1 rounded-[10px] bg-bg p-3">
      <div className="font-mono text-[22px] font-medium">{value}</div>
      <div className="text-xs text-muted">{caption}</div>
    </div>
  );
}
