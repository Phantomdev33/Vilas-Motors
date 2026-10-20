import {cp, mkdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
let backend;
try {
  backend = new URL(process.env.BACKEND_URL);
  if (backend.protocol !== 'https:' || backend.username || backend.password
      || backend.pathname !== '/' || backend.search || backend.hash
      || ['localhost', '127.0.0.1', '[::1]'].includes(backend.hostname)) {
    throw new Error();
  }
} catch {
  throw new Error('Configura BACKEND_URL en Vercel con el origen HTTPS de Render, sin /api ni credenciales.');
}

const build = spawnSync(process.execPath, ['node_modules/vite/bin/vite.js', 'build'], {
  cwd: root, stdio: 'inherit',
});
if (build.error) throw build.error;
if (build.status !== 0) process.exit(build.status ?? 1);

// Build Output API permite generar el proxy a partir del entorno de Vercel.
const output = resolve(root, '.vercel/output');
await mkdir(output, {recursive: true});
await cp(resolve(root, 'dist'), resolve(output, 'static'), {recursive: true});
await writeFile(resolve(output, 'config.json'), JSON.stringify({
  version: 3,
  routes: [
    {
      src: '/api/(.*)', dest: `${backend.origin}/api/$1`,
      headers: {'Cache-Control': 'private, no-store'},
    },
    {handle: 'filesystem'},
    {src: '/(.*)', dest: '/index.html'},
  ],
}, null, 2) + '\n');
