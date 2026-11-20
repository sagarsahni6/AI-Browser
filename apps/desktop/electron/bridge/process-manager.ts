import { spawn, type ChildProcess } from 'child_process';
import path from 'path';
import crypto from 'crypto';
import fs from 'fs';
import net from 'net';
import { EventEmitter } from 'events';
import { RpcClient } from './rpc-client';
import { SecretStorage } from '../security/secret-storage';

function findMonorepoRoot(): string {
  let curr = __dirname;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(curr, 'backend', 'app', 'main.py'))) {
      return curr;
    }
    const parent = path.dirname(curr);
    if (parent === curr) break;
    curr = parent;
  }
  return process.cwd();
}

async function findAvailablePort(startPort = 8000): Promise<number> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, '127.0.0.1', () => {
      server.close(() => resolve(startPort));
    });
    server.on('error', () => {
      resolve(findAvailablePort(startPort + 1));
    });
  });
}

export class ProcessManager extends EventEmitter {
  private child: ChildProcess | null = null;
  private rpcClient: RpcClient;
  private secretToken: string;
  private port = 8000;
  private isOnline = false;

  constructor(rpcClient: RpcClient) {
    super();
    this.rpcClient = rpcClient;
    this.secretToken = crypto.randomBytes(32).toString('hex');
  }

  public getSecretToken(): string {
    return this.secretToken;
  }

  public getPort(): number {
    return this.port;
  }

  public getStatus(): { online: boolean; port: number } {
    return { online: this.isOnline, port: this.port };
  }

  public async start(): Promise<void> {
    const rootDir = findMonorepoRoot();
    const venvPythonWin = path.join(rootDir, 'backend/.venv/Scripts/python.exe');
    const pythonExe = fs.existsSync(venvPythonWin) ? venvPythonWin : 'python';

    // Find free port dynamically to prevent socket collisions
    this.port = await findAvailablePort(8000);

    console.log(`[ProcessManager] Monorepo root: ${rootDir}`);
    console.log(`[ProcessManager] Spawning Python backend on port ${this.port} using: ${pythonExe}`);

    let storedApiKey = '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';
    try {
      const secretStorage = new SecretStorage();
      const loaded = secretStorage.getSecret('NVIDIA_API_KEY');
      if (loaded) storedApiKey = loaded;
      else secretStorage.setSecret('NVIDIA_API_KEY', storedApiKey);
    } catch (e) {
      // safeStorage fallback
    }

    const env = {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: this.port.toString(),
      SECRET_TOKEN: this.secretToken,
      NVIDIA_API_KEY: storedApiKey,
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1',
      PYTHONLEGACYWINDOWSSTDIO: '0',
      PYTHONPATH: `${rootDir};${path.join(rootDir, 'backend')}`
    };

    this.child = spawn(pythonExe, ['-m', 'backend.app.main'], {
      cwd: rootDir,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    if (this.child.stdin && this.child.stdout) {
      this.rpcClient.setStreams(this.child.stdin, this.child.stdout);
    }

    if (this.child.stderr) {
      this.child.stderr.on('data', (data: Buffer) => {
        const text = data.toString('utf-8').trim();
        if (text) {
          console.error(`[Python stderr] ${text}`);
        }
      });
    }

    this.rpcClient.on('ready', (readyMsg: { port?: number }) => {
      this.isOnline = true;
      if (readyMsg.port) {
        this.port = readyMsg.port;
      }
      console.log(`[ProcessManager] Python backend READY on 127.0.0.1:${this.port}`);
      this.emit('status', { online: true, port: this.port });
    });

    this.child.on('error', (err) => {
      console.error('[ProcessManager] Python process error:', err);
      this.isOnline = false;
      this.emit('status', { online: false, port: this.port });
    });

    this.child.on('exit', (code, signal) => {
      console.log(`[ProcessManager] Python process exited with code ${code}, signal ${signal}`);
      this.isOnline = false;
      this.emit('status', { online: false, port: this.port });
    });
  }

  public stop(): void {
    if (this.child) {
      console.log('[ProcessManager] Terminating Python backend...');
      this.rpcClient.dispose();
      try {
        this.child.kill('SIGTERM');
      } catch (err) {
        console.warn('Error killing python child:', err);
      }
      this.child = null;
      this.isOnline = false;
    }
  }
}
