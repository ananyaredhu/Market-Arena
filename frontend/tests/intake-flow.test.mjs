import test from 'node:test';
import assert from 'node:assert/strict';
import { tsLoader } from './helpers/load-ts.mjs';

for (const [mode, project, scenario, run] of [
  ['mock', 'proj_1', 'scn_1', 'run_42'],
  ['real', 'proj_persisted', 'scn_persisted', 'run_persisted'],
]) {
  test(`${mode} intake uses the same strict contract and opens Arena with both IDs`, async () => {
    const calls = [];
    const load = tsLoader({ './api': {
      createScenario: async id => { calls.push(['scenario', id]); return { id: scenario, project_id: project }; },
      runScenario: async id => { calls.push(['run', id]); return { run_id: run, project_id: project, scenario_id: scenario, status: 'done' }; },
    } });
    const { startProjectSimulation } = load('lib/intake-flow.ts');
    const result = await startProjectSimulation(project);
    assert.deepEqual(calls, [['scenario', project], ['run', scenario]]);
    assert.equal(result.href, `/project/${project}?run=${run}`);
  });
}

const { assertScenarioForProject, assertRunForScenario } = tsLoader()('lib/intake-flow.ts');
test('malformed or unrelated scenarios are rejected without a mock bypass', () => {
  for (const response of [null, {}, { id: '', project_id: 'proj_a' }, { id: 'scn_a' }, { id: 'scn_a', project_id: 'proj_b' }]) {
    assert.throws(() => assertScenarioForProject(response, 'proj_a'));
  }
});

test('missing/mismatched project, scenario and run IDs or incomplete simulation status are rejected', () => {
  const valid = { run_id: 'run_a', project_id: 'proj_a', scenario_id: 'scn_a', status: 'done' };
  for (const change of [{ run_id: undefined }, { run_id: '' }, { project_id: undefined }, { project_id: 'proj_b' },
    { scenario_id: undefined }, { scenario_id: 'scn_b' }, { status: 'running' }]) {
    assert.throws(() => assertRunForScenario({ ...valid, ...change }, 'proj_a', 'scn_a'));
  }
});

test('a mismatched scenario never reaches the run endpoint', async () => {
  const load = tsLoader({ './api': {
    createScenario: async () => ({ id: 'scn_b', project_id: 'proj_b' }),
    runScenario: async () => { assert.fail('must not run another project scenario'); },
  } });
  await assert.rejects(load('lib/intake-flow.ts').startProjectSimulation('proj_a'));
});
