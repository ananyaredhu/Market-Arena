import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { tsLoader } from './helpers/load-ts.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const script = `
import os,socket,tempfile,json,sys
from pathlib import Path
def denied(*a,**k): raise AssertionError('Offline flow must not access a network')
socket.socket.connect=denied
socket.create_connection=denied
socket.getaddrinfo=denied
for key in list(os.environ):
    if key.startswith('TELEGRAM_'): os.environ.pop(key)
os.environ['MOCK']=sys.argv[1]
os.environ['LLM_MODE']='mock'
os.environ['COUNCIL_ENGINE']='engine'
with tempfile.TemporaryDirectory(prefix='arena-frontend-flow-') as directory:
    os.environ['MARKET_ARENA_DATA_DIR']=directory
    from backend.main import app
    from fastapi.testclient import TestClient
    c=TestClient(app)
    p=c.post('/projects',json={'idea':'StudyFlow study planner for students, S$9 per month.','pack':'saas'})
    assert p.status_code==200
    project=p.json()
    s=c.post('/scenarios',json={'project_id':project['id'],'n_agents':40,'repeats':3})
    assert s.status_code==200
    scenario=s.json()
    r=c.post('/scenarios/'+scenario['id']+'/run')
    assert r.status_code==200
    run=r.json()
    kit=c.post('/runs/'+run['run_id']+'/kit',json={'project_id':project['id']})
    assert kit.status_code==200
    if sys.argv[1]=='0':
        assert (Path(directory)/(project['id']+'.json')).is_file()
        assert (Path(directory)/'runs'/(run['run_id']+'.json')).is_file()
    print(json.dumps({'project':project,'scenario':scenario,'run':run,'kit':kit.json()}))
`;

for (const mode of ['1', '0']) {
  test(`offline ${mode === '1' ? 'mock' : 'persisted real'} API responses complete frontend intake → Arena → Council/Kit`, async t => {
    const child = spawnSync('.venv/bin/python', ['-B', '-c', script, mode], {
      cwd: root, encoding: 'utf8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    });
    assert.equal(child.status, 0, child.stderr);
    const responses = JSON.parse(child.stdout);
    const calls = [];
    // Replay actual in-process backend responses through the real frontend API client.
    // No HTTP server, TCP port or external fetch is used.
    t.mock.method(globalThis, 'fetch', async (input, init) => {
      const path = new URL(input).pathname;
      calls.push({ path, body: init.body === undefined ? undefined : JSON.parse(init.body) });
      const body = path === '/projects' ? responses.project : path === '/scenarios' ? responses.scenario : responses.run;
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    const load = tsLoader({
      'next/link': { __esModule: true, default: ({ href, children, ...props }) => React.createElement('a', { href, ...props }, children) },
    });
    const { createProject } = load('lib/api.ts');
    const { startProjectSimulation } = load('lib/intake-flow.ts');
    const project = await createProject('Study planner S$9 per month', 'saas');
    const { href } = await startProjectSimulation(project.id);
    const arena = new URL(href, 'http://localhost');
    assert.equal(arena.pathname, `/project/${project.id}`);
    assert.equal(arena.searchParams.get('run'), responses.run.run_id);
    assert.deepEqual(calls.map(c => c.path), ['/projects', '/scenarios', `/scenarios/${responses.scenario.id}/run`]);
    assert.equal(calls[1].body.project_id, project.id);
    const Header = load('components/layout/AppHeader.tsx').default;
    const html = renderToStaticMarkup(React.createElement(Header, {
      active: 'arena', projectId: project.id, runContext: { projectId: project.id, runId: arena.searchParams.get('run') },
    }));
    for (const suffix of ['/council', '/kit']) {
      assert.ok(html.includes(`href="/project/${project.id}${suffix}?run=${responses.run.run_id}"`));
    }
    assert.equal(responses.kit.run_id, responses.run.run_id);
    if (mode === '0') assert.equal(responses.kit.project_id, project.id);
    else {
      assert.equal(responses.kit.project_id, null);
      assert.equal(responses.kit.scenario_origin, 'demo');
    }
  });
}
