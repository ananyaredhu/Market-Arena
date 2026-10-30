import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const load = tsLoader({});
const { chartGeometry, currentPriceNote, headline, parseCost, resultKey } = load('lib/price-finder.ts');
const { default: PriceCurve } = load('components/compare/PriceCurve.tsx');

const row = (price, share, cost) => ({
  price, share_p10: share - 0.01, share_p50: share, share_p90: share + 0.01, is_current: false,
  revenue_index: share * price * 100, ...(cost == null ? {} : { profit_index: share * (price - cost) * 100 }),
});
const data = (over = {}) => ({
  project_id: 'p', you_id: 'you', currency_symbol: 'S$', period: 'month', objective: 'revenue index', cost: null,
  current_price: 7, same_seed: 42, overrides_applied: 0, customers: 300,
  curve: [row(2, 0.2), row(4, 0.15), row(6, 0.1), row(8, 0.05), row(10, 0.02)],
  suggestion: { price: 4, share_p50: 0.15, objective: 'revenue index', revenue_index: 60 },
  band: { low: 4, high: 6, within: '5% of the best revenue index' },
  notes: ['note'], reference_prices: [], reference_note: '', ...over,
});

test('the headline and the position of the current price are plain words', () => {
  const d = data();
  assert.equal(headline(d), 'Start testing at S$4.00 per month. Prices from S$4.00 to S$6.00 come within 5% of the best revenue index.');
  assert.equal(currentPriceNote(d), 'Your current price, S$7.00, is above this band.');
  assert.equal(currentPriceNote(data({ current_price: 5 })), 'Your current price, S$5.00, is inside this band.');
  assert.equal(currentPriceNote(data({ current_price: 3 })), 'Your current price, S$3.00, is below this band.');
});

test('a band of one price says the best price is sharply peaked', () => {
  const one = data({ band: { low: 4, high: 4, within: '5% of the best revenue index' } });
  assert.equal(headline(one), 'Start testing at S$4.00 per month. No other price tried comes within 5% of the best revenue index, so the best price is sharply peaked.');
});

test('with no suggestion there is no headline, and nothing is invented', () => {
  const none = data({ suggestion: null, band: null });
  assert.equal(headline(none), null);
  assert.equal(currentPriceNote(none), null);
});

test('chart geometry keeps every point inside the plot and the best point on the curve', () => {
  const g = chartGeometry(data());
  assert.equal(g.points.length, 5);
  assert.ok(g.points.every((p) => p.x >= 44 && p.x <= 624 && p.y >= 16 && p.y <= g.baseY));
  assert.ok(g.band.x1 < g.band.x2);
  assert.ok(g.currentX > g.band.x2, 'a current price above the band is drawn to its right');
  const best = g.points.find((p) => p.price === 4);
  assert.deepEqual(g.best, { x: best.x, y: best.y });
});

test('a profit curve that dips below zero stays on the chart', () => {
  const d = data({ cost: 5, objective: 'profit index', curve: [row(5, 0.2, 5), row(6, 0.1, 5), row(2, 0.3, 5)].sort((a, b) => a.price - b.price) });
  assert.equal(resultKey(d), 'profit_index');
  const g = chartGeometry(d);
  assert.ok(g.points.every((p) => p.y >= 16 && p.y <= g.baseY));
  assert.ok(g.zeroY >= 16 && g.zeroY <= g.baseY);
});

test('a current price outside the tried range is not drawn', () => {
  assert.equal(chartGeometry(data({ current_price: 50 })).currentX, null);
});

test('the cost box takes blank or a non-negative number only', () => {
  assert.deepEqual(parseCost(''), { ok: true, cost: null });
  assert.deepEqual(parseCost(' 2.5 '), { ok: true, cost: 2.5 });
  assert.deepEqual(parseCost('0'), { ok: true, cost: 0 });
  for (const bad of ['-1', 'abc', '1,5', 'NaN']) assert.equal(parseCost(bad).ok, false, bad);
});

test('the curve ships a text table for screen readers', () => {
  const html = renderToStaticMarkup(React.createElement(PriceCurve, { data: data() }));
  assert.match(html, /role="img"/);
  assert.match(html, /<table class="sr-only">/);
  assert.equal((html.match(/<tr>/g) ?? []).length, 1 + 5);
  assert.match(html, /S\$4\.00/);
});
