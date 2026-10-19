import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const python = process.platform === 'win32'
  ? resolve(root, '.venv', 'Scripts', 'python.exe')
  : resolve(root, '.venv', 'bin', 'python');
if (!existsSync(python)) throw new Error(`Project Python environment not found: ${python}`);

const sqlitePath = resolve(root, 'output', 'e2e', 'acrn-playwright.db');
mkdirSync(dirname(sqlitePath), { recursive: true });
// Start each managed browser run from the same known seed so prior sessions,
// password attempts, and workflow mutations cannot affect qualification.
for (const suffix of ['', '-wal', '-shm']) {
  rmSync(`${sqlitePath}${suffix}`, { force: true });
}
const child = spawn(python, ['-m', 'uvicorn', 'main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8000'], {
  cwd: root,
  stdio: 'inherit',
  env: {
    ...process.env,
    ENVIRONMENT: 'test', ENABLE_DEMO_ACCOUNTS: 'true', ENABLE_DEMO_DATA: 'true',
    ENABLE_LEGACY_UNSAFE_ROUTES: 'false', SEED_DEMO_ACCOUNTS: 'true',
    DEMO_DEFAULT_PASSWORD: 'ACRN@2026', AUTH_COOKIE_SECURE: 'false', AUTH_COOKIE_SAMESITE: 'lax',
    SQLITE_PATH: sqlitePath,
  },
});

for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', code => process.exit(code ?? 0));
