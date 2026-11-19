import { createServer } from 'vite';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import electron from 'electron';
import * as esbuild from 'esbuild';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function start() {
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

  electronProcess.on('close', () => {
    server.close();
    process.exit();
  });
}

start().catch(console.error);
