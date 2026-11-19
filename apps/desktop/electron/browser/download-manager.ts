import { session, shell, type DownloadItem as ElectronDownloadItem, type WebContents } from 'electron';
import type { DownloadItem } from '@ai-browser/shared';

export type DownloadUpdateListener = (item: DownloadItem) => void;

export class DownloadManager {
  private downloads: Map<string, DownloadItem> = new Map();
  private listeners: Set<DownloadUpdateListener> = new Set();

  constructor() {
    this.setupListeners();
  }

  public subscribe(listener: DownloadUpdateListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(item: DownloadItem) {
    for (const listener of this.listeners) {
      listener(item);
    }
  }

  private setupListeners() {
    session.defaultSession.on('will-download', (_event, item: ElectronDownloadItem, _webContents: WebContents) => {
      const id = `dl-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
      const downloadInfo: DownloadItem = {
        id,
        filename: item.getFilename(),
        url: item.getURL(),
        savePath: item.getSavePath(),
        receivedBytes: item.getReceivedBytes(),
        totalBytes: item.getTotalBytes(),
        state: 'progressing',
        startTime: Date.now(),
      };

      this.downloads.set(id, downloadInfo);
      this.notify(downloadInfo);

      item.on('updated', (_evt, state) => {
        downloadInfo.receivedBytes = item.getReceivedBytes();
        downloadInfo.totalBytes = item.getTotalBytes();
        downloadInfo.savePath = item.getSavePath();
        if (state === 'interrupted') {
          downloadInfo.state = 'interrupted';
        } else if (state === 'progressing') {
          if (item.isPaused()) {
            downloadInfo.state = 'progressing';
          }
        }
        this.notify(downloadInfo);
      });

      item.once('done', (_evt, state) => {
        downloadInfo.receivedBytes = item.getReceivedBytes();
        downloadInfo.savePath = item.getSavePath();
        if (state === 'completed') {
          downloadInfo.state = 'completed';
        } else if (state === 'cancelled') {
          downloadInfo.state = 'cancelled';
        } else {
          downloadInfo.state = 'interrupted';
        }
        this.notify(downloadInfo);
      });
    });
  }

  public getDownloads(): DownloadItem[] {
    return Array.from(this.downloads.values()).sort((a, b) => b.startTime - a.startTime);
  }

  public async openFile(id: string): Promise<boolean> {
    const item = this.downloads.get(id);
    if (item && item.savePath && item.state === 'completed') {
      await shell.openPath(item.savePath);
      return true;
    }
    return false;
  }

  public openFolder(id: string): boolean {
    const item = this.downloads.get(id);
    if (item && item.savePath) {
      shell.showItemInFolder(item.savePath);
      return true;
    }
    return false;
  }
}
