import { createServer } from 'vite';
import { spawn, execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import electron from 'electron';
import * as esbuild from 'esbuild';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function freePortIfInUse(port) {
  try {
    if (process.platform === 'win32') {
      const output = execSync(`netstat -ano -p tcp | findstr :${port}`, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] });
      const lines = output.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const state = parts[3];
        const pid = parts[parts.length - 1];
        if (state === 'LISTENING' && pid && pid !== process.pid.toString()) {
          console.log(`[dev-runner] Port ${port} is occupied by PID ${pid}. Freeing port...`);
          try {
            execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
          } catch {}
        }
      }
    }
  } catch {
    // Port not in use or error querying
  }
}

async function start() {
  // Ensure port 5173 is free before launching Vite
  freePortIfInUse(5173);

  // 1. Start Vite dev server
  const server = await createServer({
    configFile: path.resolve(__dirname, 'vite.config.ts'),
    server: { port: 5173 }
  });
  await server.listen();
  console.log('Vite server running at http://localhost:5173');

  // 2. Build Electron main & preload
  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'electron/main.ts')],
    outfile: path.resolve(__dirname, 'dist/electron/main.js'),
    bundle: true,
    platform: 'node',
    target: 'node20',
    format: 'cjs',
    external: ['electron'],
    sourcemap: true,
  });

  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'electron/preload.ts')],
    outfile: path.resolve(__dirname, 'dist/electron/preload.js'),
    bundle: true,
    platform: 'node',
    target: 'node20',
    format: 'cjs',
    external: ['electron'],
    sourcemap: true,
  });

  // 3. Clean environment so Electron runs as real Electron, not as Node
  const cleanEnv = { ...process.env };
  delete cleanEnv.ELECTRON_RUN_AS_NODE;

  // 4. Launch Electron
  const electronProcess = spawn(electron, ['.'], {
    cwd: __dirname,
    stdio: 'inherit',
    env: {
      ...cleanEnv,
      NODE_ENV: 'development',
      VITE_DEV_SERVER_URL: 'http://localhost:5173'
    }
  });

  let isCleanedUp = false;
  const cleanup = () => {
    if (isCleanedUp) return;
    isCleanedUp = true;
    try {
      server.close();
    } catch {}
    try {
      if (electronProcess && !electronProcess.killed && electronProcess.pid) {
        if (process.platform === 'win32') {
          execSync(`taskkill /F /T /PID ${electronProcess.pid}`, { stdio: 'ignore' });
        } else {
          electronProcess.kill('SIGTERM');
        }
      }
    } catch {}
  };

  electronProcess.on('close', () => {
    cleanup();
    process.exit();
  });

  process.on('SIGINT', () => {
    cleanup();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    cleanup();
    process.exit(0);
  });

  process.on('exit', () => {
    cleanup();
  });
}

start().catch(console.error);
