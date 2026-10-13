// OWNER: Person A. "Market share by option, stacked by segment": for each option a pair of bars, A above B.
// Bar length = share of the whole market; coloured slices = customer segments.
import { Card, SectionLabel, SegmentDot } from "@/components/ui";
import { cx } from "@/lib/cx";
import { optionStyle, segmentStyle } from "@/lib/theme";
import type { RunResult } from "@/lib/types";

const pts = (x: number) => {
  const p = Math.round(x * 100);
  return `${p > 0 ? "+" : p < 0 ? "−" : ""}${Math.abs(p)} ${Math.abs(p) === 1 ? "pt" : "pts"}`;
};

function segmentCounts(run: RunResult, optionId: string) {
  const counts: Record<string, number> = {};
  for (const c of run.choices) if (c.choice === optionId) counts[c.segment] = (counts[c.segment] ?? 0) + 1;
  return counts;
}

function Bar({ run, optionId, scale, dashed }: { run: RunResult; optionId: string; scale: number; dashed?: boolean }) {
  const counts = segmentCounts(run, optionId);
  const share = run.totals[optionId]?.share ?? 0;
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={cx("box-border flex h-[22px] overflow-hidden rounded-md", dashed && "border border-dashed border-line-dashed")}
        style={{ width: `${Math.max(2, share * scale * 100)}%` }}
      >
        {Object.entries(counts).map(([seg, n]) => (
          <div key={seg} style={{ flex: n, background: segmentStyle(seg).color }} />
        ))}
      </div>
      <span className="font-mono text-xs text-muted">{Math.round(share * 100)}%</span>
    </div>
  );
}

export default function ShareBars({ a, b }: { a: RunResult; b: RunResult }) {
  const segments = [...new Set([...a.choices, ...b.choices].map((c) => c.segment))];
  const maxShare = Math.max(...a.option_ids.flatMap((id) => [a.totals[id].share, b.totals[id].share]));
  const scale = 0.85 / maxShare;

  return (
    <Card className="!p-[26px]">
      <div className="mb-[18px] flex flex-wrap justify-between gap-3">
        <SectionLabel>Market share by option · stacked by segment</SectionLabel>
        <div className="flex flex-wrap gap-3.5 text-[13px]">
          {segments.map((s) => (
            <span key={s} className="flex items-center gap-1.5">
              <SegmentDot segment={s} size={10} />
              {segmentStyle(s).label}
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-[22px]">
        {a.option_ids.map((id) => {
          const o = optionStyle(id);
          // Median across repeated runs, the same basis as the headline card (bars below show the first run).
          const delta = b.totals[id].p50 - a.totals[id].p50;
          return (
            <div key={id} className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <div className="flex-[0_0_150px]">
                <div className="font-bold" style={{ color: id === "you" ? "#C8F560" : "#9FB0D0" }}>{o.label}</div>
                <div className={cx("mt-0.5 font-mono text-[13px]", delta >= 0 ? "text-teal" : "text-coral")}>{pts(delta)}</div>
              </div>
              <div className="flex min-w-0 flex-[1_1_420px] flex-col gap-1.5">
                <Bar run={a} optionId={id} scale={scale} dashed={o.dashed} />
                <Bar run={b} optionId={id} scale={scale} dashed={o.dashed} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-[18px] text-xs text-muted">Top bar of each pair: Scenario A. Bottom bar: Scenario B.</div>
    </Card>
  );
}
