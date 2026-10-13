"use client";
// OWNER: Person C. MOCKUP of the bubble field (layout, colours, motion). Replace the internals freely
// (Pixi/canvas for 1,000 dots); keep the props.
// Frozen props: <Arena runResult={RunResult} onAgentClick={(agentId) => void} />
// Optional: selectedAgentId highlights the dot that is open in the Glass-Box.
import { optionStyle, segmentStyle } from "@/lib/theme";
import type { RunResult } from "@/lib/types";

interface Props {
  runResult: RunResult;
  onAgentClick: (agentId: string) => void;
  selectedAgentId?: string | null;
}

const W = 780;
const H = 760;

// Where each product bubble sits. Unknown option ids are spread on a ring (see centerFor).
const CENTERS: Record<string, { x: number; y: number }> = {
  you: { x: 270, y: 300 },
  free_tool: { x: 620, y: 165 },
  chain_app: { x: 625, y: 470 },
  outside: { x: 150, y: 570 },
};

function centerFor(id: string, index: number, total: number) {
  if (CENTERS[id]) return CENTERS[id];
  const a = (index / Math.max(1, total)) * Math.PI * 2;
  return { x: W / 2 + 280 * Math.cos(a), y: H / 2 + 280 * Math.sin(a) };
}

/** Stable 0..1 value per (id, salt) so a dot keeps the same spot inside whichever bubble it joins. */
function unit(id: string, salt: number) {
  let h = (2166136261 ^ salt) >>> 0;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return ((h >>> 0) % 10000) / 10000;
}

export default function Arena({ runResult, onAgentClick, selectedAgentId }: Props) {
  const ids = runResult.option_ids;
  const n = runResult.choices.length;
  // Radius grows with the number of dots inside, normalised to a 360-customer market like the design.
  const radius = (id: string) =>
    Math.min(150, 30 + 9 * Math.sqrt(((runResult.totals[id]?.count ?? 0) * 360) / Math.max(1, n)));
  const center = Object.fromEntries(ids.map((id, i) => [id, centerFor(id, i, ids.length)]));

  return (
    <div className="flex min-w-0 flex-1 justify-center overflow-x-auto">
      <div className="relative shrink-0" style={{ width: W, height: H }}>
        {ids.map((id) => {
          const o = optionStyle(id);
          const r = radius(id);
          return (
            <div
              key={id}
              className="bubble absolute box-border rounded-full border-2"
              style={{
                left: center[id].x - r,
                top: center[id].y - r,
                width: r * 2,
                height: r * 2,
                borderColor: o.color,
                borderStyle: o.dashed ? "dashed" : "solid",
                background: o.dashed ? "transparent" : `${o.color}10`,
              }}
            >
              <div
                className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap text-sm font-bold"
                style={{ color: o.color }}
              >
                {o.label} <span className="font-mono font-normal text-ink-soft">· {runResult.totals[id]?.count ?? 0}</span>
              </div>
            </div>
          );
        })}

        {runResult.choices.map((c) => {
          const selected = c.agent_id === selectedAgentId;
          const switched = c.prev_choice != null && c.prev_choice !== c.choice;
          const size = selected ? 16 : 10;
          const r = radius(c.choice) * 0.88 * Math.sqrt(unit(c.agent_id, 2));
          const ang = unit(c.agent_id, 1) * Math.PI * 2;
          const ctr = center[c.choice] ?? { x: W / 2, y: H / 2 };
          return (
            <button
              key={c.agent_id}
              type="button"
              aria-label={`${c.agent_id}, ${segmentStyle(c.segment).label}, chose ${optionStyle(c.choice).label}`}
              title={`${c.agent_id} · ${segmentStyle(c.segment).label} → ${optionStyle(c.choice).label}`}
              onClick={() => onAgentClick(c.agent_id)}
              className="dot absolute rounded-full p-0"
              style={{
                left: Math.round(ctr.x + r * Math.cos(ang) - size / 2),
                top: Math.round(ctr.y + r * Math.sin(ang) - size / 2),
                width: size,
                height: size,
                background: segmentStyle(c.segment).color,
                zIndex: selected ? 5 : switched ? 3 : 1,
                boxShadow: selected
                  ? "0 0 0 3px #fff, 0 0 0 8px rgba(255,255,255,0.25), 0 0 24px rgba(255,255,255,0.5)"
                  : switched
                    ? "0 0 0 2px #0B0E14, 0 0 0 3.5px #E8ECF4"
                    : "none",
              }}
            />
          );
        })}

        <div className="absolute bottom-2 left-0 text-xs text-muted">
          {n} simulated customers · ringed dots switched vs. baseline · glowing dot is open in the inspector
        </div>
      </div>
    </div>
  );
}
