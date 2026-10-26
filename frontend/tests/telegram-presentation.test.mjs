import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const load = tsLoader();
const { telegramAvailability, kitPresentationNotices } = load('components/telegram/presentation.ts');
const ResultsDashboard = load('components/telegram/ResultsDashboard.tsx').default;
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

test('observed results dashboard renders all metrics, variants, zeros, and approval state', () => {
  const html = renderToStaticMarkup(React.createElement(ResultsDashboard, {
    results: {
      approved: true,
      contacts: 0,
      variant_sizes: [2, 0],
      variants: [
        { variant: 'A', sent: 1, interested: 1, too_expensive: 0, clicks: 1, replies: 0, unsubscribes: 1 },
        { variant: 'B', sent: 0, interested: 0, too_expensive: 0, clicks: 0, replies: 0, unsubscribes: 0 },
      ],
      delivery_statuses: { delivered: 1 },
      deferred_reasons: {},
    },
  }));
  for (const label of ['Deliveries', 'Interested', 'Too expensive', 'Learn more', 'Replies', 'Unsubscribes', 'Active contacts']) {
    assert.match(html, new RegExp(label));
  }
  assert.match(html, /Observed Telegram engagement/);
  assert.match(html, /Approved/);
  assert.match(html, />A</);
  assert.match(html, />B</);
  assert.match(html, />0</);
});

test('live console defaults to read-only and confirms mutations before enabling them', () => {
  const source = fs.readFileSync(new URL('../components/telegram/LiveTelegramConsole.tsx', import.meta.url), 'utf8');
  assert.match(source, /const \[actionsEnabled, setActionsEnabled\] = useState\(false\)/);
  assert.match(source, /Enable campaign actions \(UI gate only\)/);
  assert.match(source, /setActionsEnabled\(false\)/);
  assert.match(source, /window\.confirm\("Approve these reviewed variants\?"\)/);
  assert.match(source, /window\.confirm\("Send this approved campaign now\?"\)/);
});

test('results loading is gated only by trimmed credentials and preserves scoped validation', () => {
  const source = fs.readFileSync(new URL('../components/telegram/LiveTelegramConsole.tsx', import.meta.url), 'utf8');
  assert.match(source, /disabled=\{busy \|\| !token\.trim\(\) \|\| !id\.trim\(\)\}/);
  assert.match(source, /refresh\(ticket, id\.trim\(\)\)/);
  assert.match(source, /campaignPath\(scope, campaignId, "results"\)/);
  assert.match(source, /assertCampaignIdentity\(scope, campaignId, next\)/);
  assert.match(source, /Enter the operator token/);
  assert.match(source, /Enter a campaign ID/);
  assert.match(source, /setMessage\(reason\)/);
  assert.match(source, /setActionsEnabled\(false\)/);
});
