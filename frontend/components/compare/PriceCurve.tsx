// OWNER: Person A. Result of the price finder as a curve: your simulated result at each price tried, the best price,
// the band of prices near it, and your current price. A table with the same numbers is kept for screen readers.
import { CHART, chartGeometry, resultKey } from "@/lib/price-finder";
import type { PriceSuggestResponse } from "@/lib/types";

export default function PriceCurve({ data }: { data: PriceSuggestResponse }) {
  const g = chartGeometry(data);
  const key = resultKey(data);
  const label = data.objective;
  const s = data.currency_symbol;
  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${CHART.width} ${CHART.height}`}
        role="img"
        aria-label={`${label} by price, from ${s}${g.lo.toFixed(2)} to ${s}${g.hi.toFixed(2)}`}
        className="h-auto w-full"
      >
        {g.band && (
          <rect x={g.band.x1} y={CHART.top} width={Math.max(2, g.band.x2 - g.band.x1)} height={g.baseY - CHART.top} className="fill-accent/15" />
        )}
        <line x1={CHART.left} x2={CHART.width - CHART.right} y1={g.zeroY} y2={g.zeroY} className="stroke-line-3" strokeWidth={1} />
        {g.currentX != null && (
          <line x1={g.currentX} x2={g.currentX} y1={CHART.top} y2={g.baseY} className="stroke-ink-soft" strokeDasharray="4 4" />
        )}
        <polyline points={g.line} fill="none" className="stroke-accent" strokeWidth={2.5} strokeLinejoin="round" />
        {g.best && <circle cx={g.best.x} cy={g.best.y} r={6} className="fill-accent stroke-bg" strokeWidth={2} />}
        <text x={CHART.left} y={CHART.height - 8} className="fill-muted font-mono text-[11px]">{`${s}${g.lo.toFixed(2)}`}</text>
        <text x={CHART.width - CHART.right} y={CHART.height - 8} textAnchor="end" className="fill-muted font-mono text-[11px]">{`${s}${g.hi.toFixed(2)}`}</text>
        {g.currentX != null && (
          <text x={g.currentX + 5} y={CHART.top + 10} className="fill-ink-soft font-mono text-[11px]">your price</text>
        )}
      </svg>
      <figcaption className="mt-1 text-xs text-muted">
        {label.charAt(0).toUpperCase() + label.slice(1)} per 100 customers (median share × price{data.cost != null ? " − cost" : ""} × 100). Shaded: prices within
        5% of the best. Dashed: your current price.
      </figcaption>
      <table className="sr-only">
        <caption>{label} at each price tried</caption>
        <thead>
          <tr>
            <th scope="col">Price</th>
            <th scope="col">Share (median)</th>
            <th scope="col">{label}</th>
          </tr>
        </thead>
        <tbody>
          {data.curve.map((r) => (
            <tr key={r.price}>
              <td>{`${s}${r.price.toFixed(2)}`}</td>
              <td>{`${(r.share_p50 * 100).toFixed(1)}%`}</td>
              <td>{(r[key] ?? 0).toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
