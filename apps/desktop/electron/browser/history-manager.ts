import { app } from 'electron';
import path from 'path';
import fs from 'fs';
import type { HistoryItem } from '@ai-browser/shared';

export class HistoryManager {
  private filePath: string;
  private history: HistoryItem[] = [];

  constructor() {
    const userData = app?.getPath ? app.getPath('userData') : process.cwd();
    this.filePath = path.join(userData, 'browser_history.json');
    this.load();
  }

  private load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf-8');
        this.history = JSON.parse(raw);
      }
    } catch (e) {
      console.warn('Failed to load history:', e);
      this.history = [];
    }
  }

  private save() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.history.slice(0, 2000), null, 2), 'utf-8');
    } catch (e) {
      console.warn('Failed to save history:', e);
    }
  }

  public addEntry(url: string, title: string, isPrivate = false) {
    if (isPrivate || !url || url.startsWith('about:') || url.startsWith('chrome:')) {
      return;
    }

    const existingIdx = this.history.findIndex(item => item.url === url);
    if (existingIdx !== -1) {
      const item = this.history[existingIdx];
      item.title = title || item.title;
      item.visitedAt = Date.now();
      item.visitCount += 1;
      // Move to top
      this.history.splice(existingIdx, 1);
      this.history.unshift(item);
    } else {
      const newItem: HistoryItem = {
        id: `hist-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
        url,
        title: title || url,
        visitedAt: Date.now(),
        visitCount: 1,
      };
      this.history.unshift(newItem);
    }

    this.save();
  }

  public getHistory(limit = 100): HistoryItem[] {
    return this.history.slice(0, limit);
  }

  public search(query: string, limit = 20): HistoryItem[] {
    const q = query.toLowerCase().trim();
    if (!q) return this.getHistory(limit);

    return this.history
      .filter(h => h.url.toLowerCase().includes(q) || h.title.toLowerCase().includes(q))
      .slice(0, limit);
  }

  public clear() {
    this.history = [];
    this.save();
  }
}
