#!/usr/bin/env node
// No npm dependencies. Spawn programs with argument arrays, never a shell string.
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const python = process.env.PAINT_PRO_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
export const commands = ['start', 'test', 'test-js', 'doctor', 'build-native', 'package', 'help'];

export function run(program, args, options = {}) {
  const result = spawnSync(program, args, { cwd: root, stdio: 'inherit', shell: false, ...options });
  if (result.error) throw new Error(`Não foi possível executar ${program}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`${program} terminou com código ${result.status ?? result.signal}`);
  return result;
}

export function isSourceFile(path) {
  // Explicit source allowlist: never bundle .git, environments, DLLs or user images.
  const normalized = path.split(sep).join('/');
  if (normalized.split('/').some(part => part.startsWith('.') && !['.github', '.gitignore'].includes(part))) return false;
  if (normalized.split('/').some(part => ['__pycache__', 'node_modules', 'build', 'bin', 'dist'].includes(part))) return false;
  return ['app.py', 'classic.py', 'document.py', 'native_backend.py', 'clipboard_bridge.py', 'editor_dialogs.py', 'test_editor.py', 'test_native.py', 'test_clipboard.py',
    'requirements.txt', 'README.md', 'LICENSE', '.gitignore', 'package.json'].includes(normalized)
    || /^(scripts\/[^/]+\.mjs|native\/(paintpro\.cpp|CMakeLists\.txt)|\.github\/workflows\/ci\.yml)$/.test(normalized);
}

export function main(command = 'help') {
  if (!commands.includes(command)) throw new Error(`Comando desconhecido: ${command}. Use help.`);
  if (command === 'help') {
    console.log('Paint Pro: node scripts/dev.mjs <comando>\n' + commands.join(' | '));
  } else if (command === 'start') {
    run(python, ['app.py']);
  } else if (command === 'test-js') {
    run(process.execPath, ['--test', 'scripts/dev.test.mjs']);
  } else if (command === 'test') {
    main('test-js');
    run(python, ['-m', 'unittest', '-v']);
  } else if (command === 'doctor') {
    console.log(`Node ${process.version}; Python: ${python}`);
    run(python, ['-c', "import sys, tkinter, customtkinter, PIL; from native_backend import backend_name; print('Python:', sys.version); print('CustomTkinter:', customtkinter.__version__); print('Pillow:', PIL.__version__); print('Motor de preenchimento:', backend_name())"]);
  } else if (command === 'build-native') {
    run('cmake', ['-S', 'native', '-B', 'build/native', '-DCMAKE_BUILD_TYPE=Release']);
    run('cmake', ['--build', 'build/native', '--config', 'Release']);
    run(python, ['-c', "from native_backend import backend_name; assert backend_name() == 'C++17', 'Biblioteca compilada não carregou'; print('C++17 carregado com sucesso')"]);
  } else if (command === 'package') {
    const tracked = run('git', ['ls-files', '-z', '--cached', '--others', '--exclude-standard'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'inherit'] });
    const files = [...new Set(tracked.stdout.split('\0').filter(Boolean).filter(isSourceFile))].sort();
    if (!files.includes('app.py')) throw new Error('Pasta de projeto inválida');
    mkdirSync(resolve(root, 'dist'), { recursive: true });
    const script = "import json, sys, zipfile; files=json.load(sys.stdin); z=zipfile.ZipFile('dist/paint-pro-source.zip','w',zipfile.ZIP_DEFLATED); [z.write(p, 'paint-pro/'+p) for p in files]; z.close(); print('Criado: dist/paint-pro-source.zip')";
    run(python, ['-c', script], { input: JSON.stringify(files), stdio: ['pipe', 'inherit', 'inherit'] });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv[2]); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
