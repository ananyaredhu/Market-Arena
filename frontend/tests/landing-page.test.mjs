import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const css = new Proxy({}, { get: (_target, key) => String(key) });
const load = tsLoader({
  'next/link': {
    __esModule: true,
    default: ({ href, children, ...props }) => React.createElement('a', { href, ...props }, children),
  },
  './landing.module.css': { __esModule: true, default: css },
});

const { buildCustomers, renderPreview } = load('lib/landing-preview.ts');
const { default: LandingPage } = load('components/landing/LandingPage.tsx');

test('illustrative preview is deterministic and prices move the demo share', () => {
  const customers = buildCustomers();
  assert.equal(customers.length, 240);
  const base = renderPreview(customers, 1);
  const again = renderPreview(buildCustomers(), 1);
  assert.equal(base.youPct, again.youPct);
  assert.equal(base.deltaText, 'baseline');
  assert.equal(base.pills.map((pill) => pill.label).join(','), 'S$7,S$9,S$12');
  assert.equal(base.pills[1].on, true);
  assert.equal(base.bubbles.reduce((sum, bubble) => sum + bubble.count, 0), 240);
  assert.equal(base.dots.length, 240);
  const low = renderPreview(customers, 0);
  const high = renderPreview(customers, 2);
  assert.notEqual(low.youPct, base.youPct);
  assert.notEqual(high.youPct, base.youPct);
  assert.match(low.deltaText, /pts$/);
  assert.match(base.youRange, /%$/);
});

test('landing page keeps the reference sections and sends simulations to intake', () => {
  const html = renderToStaticMarkup(React.createElement(LandingPage));
  for (const copy of [
    'Test your startup against a market that',
    'fights back.',
    'How it works',
    'From idea to evidence in four moves.',
    'Not another AI that tells you your idea is great.',
    'Math decides, language explains',
    'Everything a founder needs to decide what to test next.',
    'See why every customer chose, and overrule it.',
    'A verdict with a fragility score.',
    'Change one thing, compare two markets.',
    'Close the loop with real evidence.',
    'We don’t predict your revenue.',
    'what to test next.',
    'Start free. Pay when it earns it.',
    'S$0',
    'S$19',
    'S$299',
    'Recommended',
    'Find out before you build.',
    'Illustrative preview',
    'StudyFlow',
    'Glass-Box · a17',
    '© 2026 Market Arena',
    'Simulated outcomes under stated assumptions. Not financial advice.',
  ]) {
    assert.ok(html.includes(copy), `missing: ${copy}`);
  }
  const intakeLinks = html.match(/href="\/intake"/g) ?? [];
  assert.equal(intakeLinks.length, 3);
  assert.ok(html.includes('href="#how"'));
  assert.ok(html.includes('href="#features"'));
  assert.ok(html.includes('href="#pricing"'));
  assert.ok(html.includes('href="#top"'));
  assert.ok(html.includes('S$7'));
  assert.ok(html.includes('S$9'));
  assert.ok(html.includes('S$12'));
});
