import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import Module from 'node:module';
import ts from 'typescript';
const filename = fileURLToPath(new URL('../components/telegram/campaign-state.ts', import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017 },
}).outputText;
const mod = new Module(filename);
mod._compile(compiled, filename);
const { CampaignRequestGate, campaignPath, assertCampaignIdentity } = mod.exports;

test('pending actions cannot overlap and stale responses cannot replace current state', () => {
  const gate = new CampaignRequestGate();
  const first = gate.begin();
  assert.notEqual(first, null);
  assert.equal(gate.begin(), null);
  gate.invalidate();
  const second = gate.begin();
  assert.equal(gate.current(first), false);
  assert.equal(gate.finish(first), false);
  assert.equal(gate.current(second), true);
  assert.equal(gate.finish(second), true);
  assert.equal(gate.current(second), false);
});

test('every campaign operation carries project and run scope', () => {
  for (const operation of ['results', 'approve', 'send']) {
    const url = new URL(campaignPath({ projectId: 'proj_a', runId: 'run_b' }, 'cmp_a', operation), 'http://localhost');
    assert.equal(url.pathname, `/telegram/campaigns/cmp_a/${operation}`);
    assert.equal(url.searchParams.get('project_id'), 'proj_a');
    assert.equal(url.searchParams.get('run_id'), 'run_b');
  }
});

test('a response for another campaign, run or project cannot be displayed', () => {
  const scope = { projectId: 'proj_a', runId: 'run_a' };
  const response = { id: 'cmp_a', project_id: 'proj_a', run_id: 'run_a' };
  assert.doesNotThrow(() => assertCampaignIdentity(scope, 'cmp_a', response));
  for (const key of ['id', 'project_id', 'run_id']) {
    assert.throws(() => assertCampaignIdentity(scope, 'cmp_a', { ...response, [key]: 'unrelated' }));
  }
});
