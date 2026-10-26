import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const load = tsLoader();
const { telegramAvailability, kitPresentationNotices } = load('components/telegram/presentation.ts');
const legacy = 'Telegram delivery, approval and measured click rates are not live. Variant text comes from this kit.';

test('presentation removes only the obsolete delivery notice and does not mutate the Kit', () => {
  const source = Object.freeze([legacy, 'Café priors are illustrative.', 'Do not send without consent.']);
  assert.deepEqual(kitPresentationNotices(source), source.slice(1));
  assert.equal(source[0], legacy);
});

test('mode selection and a reachable backend never imply configured or confirmed delivery', () => {
  assert.match(telegramAvailability('checking', 'unverified'), /not yet verified/);
  assert.match(telegramAvailability('real', 'unverified'), /configuration is not yet verified/);
  assert.match(telegramAvailability('real', 'unconfigured'), /configuration is incomplete/);
  assert.match(telegramAvailability('offline', 'confirmed'), /Backend unavailable/);
  assert.match(telegramAvailability('mock', 'unverified'), /Delivery is simulated/);
  assert.match(telegramAvailability('real', 'confirmed'), /successful send in this campaign/);
});

test('mock TelegramConsole explicitly labels simulated delivery and sample metrics', () => {
  const Console = load('components/telegram/TelegramConsole.tsx').default;
  const html = renderToStaticMarkup(React.createElement(Console, {
    contacts: 2, variants: ['A', 'B'], variantSizes: [1, 1], results: [{ variant: 'A', rate: 0 }],
  }));
  assert.match(html, /simulated/);
  assert.match(html, /sample/);
  assert.doesNotMatch(html, /NaN/);
});
