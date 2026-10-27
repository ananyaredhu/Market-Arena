import fs from 'node:fs';
import path from 'node:path';
import Module from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = fileURLToPath(new URL('../../', import.meta.url));
/** Transpile local TS in memory; no generated files or extra test dependencies. */
export function tsLoader(stubs = {}) {
  const cache = new Map();
  function load(input) {
    let file = path.isAbsolute(input) ? input : path.resolve(root, input);
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) file = ['.ts', '.tsx', '/index.ts', '/index.tsx'].map(ext => file + ext).find(p => fs.existsSync(p));
    if (!file) throw new Error(`Cannot resolve test module ${input}`);
    if (cache.has(file)) return cache.get(file).exports;
    const mod = new Module(file);
    mod.paths = Module._nodeModulePaths(path.dirname(file));
    const normalRequire = mod.require.bind(mod);
    mod.require = name => {
      if (Object.hasOwn(stubs, name)) return stubs[name];
      if (name.startsWith('@/')) return load(path.resolve(root, name.slice(2)));
      if (name.startsWith('.')) return load(path.resolve(path.dirname(file), name));
      return normalRequire(name);
    };
    cache.set(file, mod);
    mod._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017,
        jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText, file);
    return mod.exports;
  }
  return load;
}
