// OWNER: Person A. Pure helpers for the price finder (POST /pricing/suggest): chart geometry and the plain-words summary.
import type { PriceSuggestResponse } from "./types";

export const CHART = { width: 640, height: 240, left: 44, right: 16, top: 16, bottom: 34 } as const;

export function resultKey(d: Pick<PriceSuggestResponse, "cost">): "profit_index" | "revenue_index" {
  return d.cost == null ? "revenue_index" : "profit_index";
}

/** Chart coordinates for the curve, the best point, the suggested band and the current price. */
export function chartGeometry(d: PriceSuggestResponse) {
  const key = resultKey(d);
  const prices = d.curve.map((r) => r.price);
  const lo = Math.min(...prices);
  const hi = Math.max(...prices);
  const values = d.curve.map((r) => r[key] ?? 0);
  const top = Math.max(...values, 0);
  const bottom = Math.min(...values, 0);
  const span = top - bottom || 1;
  const w = CHART.width - CHART.left - CHART.right;
  const h = CHART.height - CHART.top - CHART.bottom;
  const x = (price: number) => CHART.left + (hi === lo ? w / 2 : ((price - lo) / (hi - lo)) * w);
  const y = (value: number) => CHART.top + (1 - (value - bottom) / span) * h;
  const points = d.curve.map((r) => ({ price: r.price, value: r[key] ?? 0, x: x(r.price), y: y(r[key] ?? 0) }));
  return {
    points,
    line: points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "),
    zeroY: y(0),
    best: d.suggestion ? { x: x(d.suggestion.price), y: y(d.curve.find((r) => r.price === d.suggestion!.price)?.[key] ?? 0) } : null,
    band: d.band ? { x1: x(d.band.low), x2: x(d.band.high) } : null,
    currentX: d.current_price >= lo && d.current_price <= hi ? x(d.current_price) : null,
    lo,
    hi,
    baseY: CHART.top + h,
  };
}

const money = (symbol: string, v: number) => `${symbol}${v.toFixed(2)}`;

/** One sentence on where the user's current price sits against the suggestion. */
export function currentPriceNote(d: PriceSuggestResponse): string | null {
  if (!d.suggestion || !d.band) return null;
  const now = d.current_price;
  const where =
    now < d.band.low ? "below" : now > d.band.high ? "above" : null;
  if (where == null) return `Your current price, ${money(d.currency_symbol, now)}, is inside this band.`;
  return `Your current price, ${money(d.currency_symbol, now)}, is ${where} this band.`;
}

export function headline(d: PriceSuggestResponse): string | null {
  if (!d.suggestion || !d.band) return null;
  const s = d.currency_symbol;
  const start = `Start testing at ${money(s, d.suggestion.price)} per ${d.period}.`;
  if (d.band.low === d.band.high) {
    return `${start} No other price tried comes within ${d.band.within}, so the best price is sharply peaked.`;
  }
  return `${start} Prices from ${money(s, d.band.low)} to ${money(s, d.band.high)} come within ${d.band.within}.`;
}

/** The cost box accepts blank (revenue index) or a non-negative number. */
export function parseCost(text: string): { ok: boolean; cost: number | null } {
  const t = text.trim();
  if (t === "") return { ok: true, cost: null };
  const n = Number(t);
  return Number.isFinite(n) && n >= 0 ? { ok: true, cost: n } : { ok: false, cost: null };
}
