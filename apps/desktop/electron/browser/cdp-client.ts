import type { WebContents } from 'electron';

export class CdpClient {
  private webContents: WebContents;
  private attached = false;

  constructor(webContents: WebContents) {
    this.webContents = webContents;
  }

  public async attach(): Promise<void> {
    if (this.attached || this.webContents.isDestroyed()) return;
    try {
      if (!this.webContents.debugger.isAttached()) {
        this.webContents.debugger.attach('1.3');
      }
      this.attached = true;
    } catch (err) {
      console.error('Failed to attach debugger:', err);
      throw err;
    }
  }

  public detach(): void {
    if (this.webContents.isDestroyed()) {
      this.attached = false;
      return;
    }
    try {
      if (this.webContents.debugger.isAttached()) {
        this.webContents.debugger.detach();
      }
    } catch (err) {
      console.warn('Error detaching debugger:', err);
    } finally {
      this.attached = false;
    }
  }

  public async sendCommand<T = any>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (!this.attached) {
      await this.attach();
    }
    return this.webContents.debugger.sendCommand(method, params);
  }
}
