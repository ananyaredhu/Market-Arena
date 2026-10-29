/**
 * Illustrative arena preview for the landing page.
 * Ported from the design reference so the dots, shares and ranges match that
 * demo. These figures are not an engine run and not a real market result.
 */

export const PREVIEW_CUSTOMERS = 240;

export type Segment = "budget" | "power" | "busy" | "skeptic";
export type ModeIndex = 0 | 1 | 2;
type ModeName = "low" | "base" | "high";

export type Customer = {
  seg: Segment;
  c: string;
  u: number;
  ang: number;
  rad: number;
};

export type PreviewBubble = {
  left: number;
  top: number;
  w: number;
  label: string;
  stroke: string;
  fill: string;
  dash: string;
  glow: string;
  count: number;
};

export type PreviewDot = {
  x: string;
  y: string;
  c: string;
  z: number;
  sh: string;
};

export type PreviewRow = {
  label: string;
  stroke: string;
  pct: number;
  bar: number;
};

export type PreviewPill = {
  label: string;
  on: boolean;
};

export type ArenaPreviewModel = {
  bubbles: PreviewBubble[];
  dots: PreviewDot[];
  hero: { x: string; y: string };
  rows: PreviewRow[];
  pills: PreviewPill[];
  youPct: number;
  youRange: string;
  deltaText: string;
  deltaColor: string;
};

const SEGMENTS: readonly [Segment, number, string][] = [
  ["budget", 0.32, "#FF7A6B"],
  ["power", 0.22, "#34D3BE"],
  ["busy", 0.3, "#F6B93B"],
  ["skeptic", 0.16, "#A98BFF"],
];

const MODES: readonly ModeName[] = ["low", "base", "high"];

const CHOICE: Record<ModeName, Record<Segment, readonly [number, number, number, number]>> = {
  low: {
    budget: [0.46, 0.3, 0.07, 0.17],
    power: [0.62, 0.12, 0.17, 0.09],
    busy: [0.38, 0.09, 0.4, 0.13],
    skeptic: [0.1, 0.19, 0.19, 0.52],
  },
  base: {
    budget: [0.2, 0.57, 0.08, 0.15],
    power: [0.55, 0.15, 0.2, 0.1],
    busy: [0.3, 0.1, 0.45, 0.15],
    skeptic: [0.07, 0.2, 0.21, 0.52],
  },
  high: {
    budget: [0.07, 0.64, 0.09, 0.2],
    power: [0.45, 0.18, 0.25, 0.12],
    busy: [0.2, 0.12, 0.5, 0.18],
    skeptic: [0.04, 0.2, 0.22, 0.54],
  },
};

const COMPETITORS = [
  { label: "StudyFlow (you)", x: 220, y: 300, stroke: "#C8F560", fill: "rgba(200,245,96,0.07)", dash: "solid", glow: "0 0 60px rgba(200,245,96,0.28), inset 0 0 40px rgba(200,245,96,0.08)" },
  { label: "FreeTool", x: 540, y: 150, stroke: "#7C8DB0", fill: "rgba(124,141,176,0.06)", dash: "solid", glow: "0 0 40px rgba(124,141,176,0.18)" },
  { label: "ChainApp", x: 790, y: 410, stroke: "#7C8DB0", fill: "rgba(124,141,176,0.06)", dash: "solid", glow: "0 0 40px rgba(124,141,176,0.18)" },
  { label: "Do nothing", x: 90, y: 470, stroke: "#7C8DB0", fill: "transparent", dash: "dashed", glow: "none" },
] as const;

const PRICE_LABELS = ["S$7", "S$9", "S$12"] as const;

function makeRng(seed = 7) {
  let s = seed;
  return () => {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function buildCustomers(): Customer[] {
  const rnd = makeRng(7);
  const out: Customer[] = [];
  for (let i = 0; i < PREVIEW_CUSTOMERS; i++) {
    const u = rnd();
    let acc = 0;
    let seg: readonly [Segment, number, string] = SEGMENTS[3];
    for (const group of SEGMENTS) {
      acc += group[1];
      if (u < acc) {
        seg = group;
        break;
      }
    }
    out.push({ seg: seg[0], c: seg[2], u: rnd(), ang: rnd() * Math.PI * 2, rad: rnd() });
  }
  return out;
}

function choose(customer: Customer, mode: ModeName) {
  const weights = CHOICE[mode][customer.seg];
  let acc = 0;
  for (let k = 0; k < 4; k++) {
    acc += weights[k];
    if (customer.u < acc) return k;
  }
  return 3;
}

export function renderPreview(customers: Customer[], modeIndex: ModeIndex): ArenaPreviewModel {
  const mode = MODES[modeIndex];
  const current = customers.map((customer) => choose(customer, mode));
  const baseline = customers.map((customer) => choose(customer, "base"));
  const counts = [0, 0, 0, 0];
  const base = [0, 0, 0, 0];
  current.forEach((choice) => {
    counts[choice] += 1;
  });
  baseline.forEach((choice) => {
    base[choice] += 1;
  });
  const total = customers.length;
  const radii = counts.map((count) => 30 + 9 * Math.sqrt(count));
  const bubbles: PreviewBubble[] = COMPETITORS.map((competitor, index) => ({
    left: (competitor.x - radii[index]) / 10,
    top: (competitor.y - radii[index]) / 5.8,
    w: radii[index] / 5,
    label: competitor.label,
    stroke: competitor.stroke,
    fill: competitor.fill,
    dash: competitor.dash,
    glow: competitor.glow,
    count: counts[index],
  }));
  const dots: PreviewDot[] = customers.map((customer, index) => {
    const choice = current[index];
    const switched = mode !== "base" && choice !== baseline[index];
    const radius = radii[choice] * 0.88 * Math.sqrt(customer.rad);
    return {
      x: ((COMPETITORS[choice].x + radius * Math.cos(customer.ang)) / 10).toFixed(2),
      y: ((COMPETITORS[choice].y + radius * Math.sin(customer.ang)) / 5.8).toFixed(2),
      c: customer.c,
      z: switched ? 3 : 1,
      sh: switched ? `0 0 0 2px #0B0E14, 0 0 0 3.5px #fff, 0 0 12px ${customer.c}` : `0 0 8px ${customer.c}`,
    };
  });
  const heroRadius = radii[1] * 0.4;
  const share = counts[0] / total;
  const margin = 2.2 * 1.28 * Math.sqrt((share * (1 - share)) / total);
  const deltaPoints = Math.round(((counts[0] - base[0]) / total) * 100);
  return {
    bubbles,
    dots,
    hero: {
      x: ((COMPETITORS[1].x + heroRadius * Math.cos(0.9)) / 10).toFixed(2),
      y: ((COMPETITORS[1].y + heroRadius * Math.sin(0.9)) / 5.8).toFixed(2),
    },
    rows: COMPETITORS.map((competitor, index) => ({
      label: competitor.label.replace(" (you)", ""),
      stroke: competitor.stroke,
      pct: Math.round((counts[index] / total) * 100),
      bar: Math.min(100, Math.round(((counts[index] / total) * 100) / 0.6)),
    })),
    pills: PRICE_LABELS.map((label, index) => ({ label, on: modeIndex === index })),
    youPct: Math.round(share * 100),
    youRange: `${Math.round((share - margin) * 100)}\u2013${Math.round((share + margin) * 100)}%`,
    deltaText: deltaPoints === 0 ? "baseline" : `${deltaPoints > 0 ? "\u25B2 +" : "\u25BC \u2212"}${Math.abs(deltaPoints)} pts`,
    deltaColor: deltaPoints >= 0 ? "#C8F560" : "#FF7A6B",
  };
}
