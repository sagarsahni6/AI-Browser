import { EventEmitter } from 'events';
import type { Writable, Readable } from 'stream';
import type { JsonRpcRequest, JsonRpcResponse, JsonRpcNotification } from '@ai-browser/shared';

interface PendingRequest {
  resolve: (value: any) => void;
  reject: (reason: any) => void;
  timer: NodeJS.Timeout;
}

export type RpcMethodHandler = (params: any) => Promise<any>;

export class RpcClient extends EventEmitter {
  private stdin: Writable | null = null;
  private stdout: Readable | null = null;
  private nextId = 1;
  private pendingRequests = new Map<string | number, PendingRequest>();
  private methodHandlers = new Map<string, RpcMethodHandler>();
  private buffer = '';

  public setStreams(stdin: Writable, stdout: Readable) {
    this.stdin = stdin;
    this.stdout = stdout;

    this.stdout.on('data', (chunk: Buffer) => {
      this.buffer += chunk.toString('utf-8');
      this.processBuffer();
    });
  }

  public registerMethod(method: string, handler: RpcMethodHandler) {
    this.methodHandlers.set(method, handler);
  }

  private processBuffer() {
    let newlineIdx: number;
    while ((newlineIdx = this.buffer.indexOf('\n')) !== -1) {
      const line = this.buffer.slice(0, newlineIdx).trim();
      this.buffer = this.buffer.slice(newlineIdx + 1);
      if (line) {
        this.handleMessage(line);
      }
    }
  }

  private async handleMessage(raw: string) {
    let msg: any;
    try {
      msg = JSON.parse(raw);
    } catch (e) {
      console.error('[RPC] Failed to parse incoming JSON line:', raw, e);
      return;
    }

    // 1. Ready handshake or system notification
    if (msg.type === 'ready') {
      this.emit('ready', msg);
      return;
    }

    // 2. Response to an outgoing request
    if (msg.id !== undefined && (msg.result !== undefined || msg.error !== undefined)) {
      const pending = this.pendingRequests.get(msg.id);
      if (pending) {
        clearTimeout(pending.timer);
        this.pendingRequests.delete(msg.id);
        if (msg.error) {
          pending.reject(new Error(msg.error.message || 'RPC Error'));
        } else {
          pending.resolve(msg.result);
        }
      }
      return;
    }

    // 3. Incoming request from Python to Electron
    if (msg.method && msg.id !== undefined) {
      const handler = this.methodHandlers.get(msg.method);
      if (!handler) {
        this.sendResponse({
          jsonrpc: '2.0',
          id: msg.id,
          error: { code: -32601, message: `Method not found: ${msg.method}` }
        });
        return;
      }

      try {
        const result = await handler(msg.params);
        this.sendResponse({
          jsonrpc: '2.0',
          id: msg.id,
          result: result ?? null
        });
      } catch (err: any) {
        this.sendResponse({
          jsonrpc: '2.0',
          id: msg.id,
          error: { code: -32000, message: err?.message || 'Internal RPC error' }
        });
      }
      return;
    }

    // 4. Notification
    if (msg.method && msg.id === undefined) {
      this.emit(`notification:${msg.method}`, msg.params);
    }
  }

  public async call<T = any>(method: string, params: any = {}, timeoutMs = 15000): Promise<T> {
    const id = this.nextId++;
    const req: JsonRpcRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params
    };

    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`RPC request '${method}' timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pendingRequests.set(id, { resolve, reject, timer });
      this.send(req);
    });
  }

  public sendNotification(method: string, params: any = {}) {
    const notif: JsonRpcNotification = {
      jsonrpc: '2.0',
      method,
      params
    };
    this.send(notif);
  }

  private sendResponse(res: JsonRpcResponse) {
    this.send(res);
  }

  private send(msg: any) {
    if (!this.stdin || !this.stdin.writable) {
      console.warn('[RPC] Cannot send message, stdin not writable:', msg);
      return;
    }
    this.stdin.write(JSON.stringify(msg) + '\n');
  }

  public dispose() {
    for (const [, pending] of this.pendingRequests.entries()) {
      clearTimeout(pending.timer);
      pending.reject(new Error('RPC client disposed'));
    }
    this.pendingRequests.clear();
  }
}
