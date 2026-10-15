import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { isSourceFile, root } from './dev.mjs';

test('packaging includes language sources and excludes private/generated files', () => {
  for (const p of ['app.py', 'native/paintpro.cpp', 'scripts/dev.mjs', '.github/workflows/ci.yml']) assert.equal(isSourceFile(p), true, p);
  for (const p of ['.env', '.git/config', '../app.py', '.venv/app.py', 'drawing.png', 'native/bin/paintpro_native.dll', 'dist/archive.zip', 'secret.py']) assert.equal(isSourceFile(p), false, p);
});

test('CLI help works without Python or a compiler', () => {
  const result = spawnSync(process.execPath, ['scripts/dev.mjs', 'help'], { cwd: root, encoding: 'utf8' });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /build-native/);
});

test('unknown commands fail with an actionable message', () => {
  const result = spawnSync(process.execPath, ['scripts/dev.mjs', 'unknown'], { cwd: root, encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Use help/);
});
