import type { WebContents } from 'electron';
import { CdpClient } from './cdp-client';

export class DebuggerManager {
  private clients = new Map<number, CdpClient>();

  public getClient(webContents: WebContents): CdpClient {
    const id = webContents.id;
    let client = this.clients.get(id);
    if (!client) {
      client = new CdpClient(webContents);
      this.clients.set(id, client);
    }
    return client;
  }

  public removeClient(webContentsId: number): void {
    const client = this.clients.get(webContentsId);
    if (client) {
      client.detach();
      this.clients.delete(webContentsId);
    }
  }

  public dispose(): void {
    for (const [id, client] of this.clients.entries()) {
      client.detach();
    }
    this.clients.clear();
  }
}
