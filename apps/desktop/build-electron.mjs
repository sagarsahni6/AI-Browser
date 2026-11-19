import * as esbuild from 'esbuild';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function build() {
  console.log('Building Electron main and preload with esbuild...');

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

  console.log('Electron build complete.');
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
