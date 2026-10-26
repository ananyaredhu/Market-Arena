import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const load = tsLoader({
  'next/link': { __esModule: true, default: ({ href, children, ...props }) => React.createElement('a', { href, ...props }, children) },
});
const { default: Header } = load('components/layout/AppHeader.tsx');
const { projectHref, selectedRunId } = load('lib/run-context.ts');
function links(projectId, runContext) {
  const html = renderToStaticMarkup(React.createElement(Header, { active: 'arena', projectId, runContext }));
  return [...html.matchAll(/href="([^"]+)"/g)].map(m => m[1].replaceAll('&amp;', '&'));
}

test('actual shared header preserves selected run across Arena, Council and Kit', () => {
  for (const active of ['arena', 'council', 'experiments']) {
    const html = renderToStaticMarkup(React.createElement(Header, {
      active, projectId: 'proj_a', runContext: { projectId: 'proj_a', runId: 'run_a' },
    }));
    for (const route of ['/project/proj_a?run=run_a', '/project/proj_a/council?run=run_a', '/project/proj_a/kit?run=run_a']) {
      assert.ok(html.includes(`href="${route}"`));
    }
  }
});

test('header rejects a run context from another project and does not retain it in History or Compare', () => {
  const hrefs = links('proj_b', { projectId: 'proj_a', runId: 'run_a' });
  assert.ok(hrefs.includes('/project/proj_b/kit'));
  assert.ok(hrefs.every(h => !h.includes('run_a')));
  assert.equal(projectHref('proj_a', 'history', { projectId: 'proj_a', runId: 'run_a' }), '/project/proj_a/history');
  assert.equal(projectHref('proj_a', 'compare', { projectId: 'proj_a', runId: 'run_a' }), '/compare');
});

test('only the explicit demo project gets a default run; selected alternate demo runs survive navigation', () => {
  assert.equal(selectedRunId('proj_real', null), null);
  assert.equal(selectedRunId('proj_real', ''), null);
  assert.equal(selectedRunId('proj_1', null), 'run_42');
  assert.equal(selectedRunId('proj_1', 'run_42_price3'), 'run_42_price3');
  assert.ok(links('proj_1', { projectId: 'proj_1', runId: 'run_42_price3' }).includes('/project/proj_1/kit?run=run_42_price3'));
});

test('navigation encodes route and query identifiers safely', () => {
  const id = 'project/with spaces';
  const url = new URL(projectHref(id, 'experiments', { projectId: id, runId: 'run & alt' }), 'http://localhost');
  assert.equal(url.pathname, '/project/project%2Fwith%20spaces/kit');
  assert.equal(url.searchParams.get('run'), 'run & alt');
});


for (const [name, file] of [['Kit', 'app/project/[id]/kit/KitView.tsx'], ['Council', 'app/project/[id]/council/CouncilView.tsx']]) {
  test(`${name} view wires the URL project/run into its actual shared header`, async () => {
    const { renderToPipeableStream } = await import('react-dom/server');
    const { PassThrough } = await import('node:stream');
    const viewLoad = tsLoader({
      'next/link': { __esModule: true, default: ({ href, children, ...props }) => React.createElement('a', { href, ...props }, children) },
      'next/navigation': { useSearchParams: () => new URLSearchParams('run=run_selected') },
    });
    const View = viewLoad(file).default;
    const html = await new Promise((resolve, reject) => {
      const sink = new PassThrough();
      let output = '';
      sink.on('data', chunk => { output += chunk; });
      sink.on('end', () => resolve(output));
      sink.on('error', reject);
      const stream = renderToPipeableStream(React.createElement(View, { params: Promise.resolve({ id: 'proj_selected' }) }), {
        onAllReady() { stream.pipe(sink); }, onError: reject,
      });
    });
    assert.ok(html.includes('/project/proj_selected?run=run_selected'));
    assert.ok(html.includes('/project/proj_selected/council?run=run_selected'));
    assert.ok(html.includes('/project/proj_selected/kit?run=run_selected'));
    assert.ok(!html.includes('run_42'));
  });
}
