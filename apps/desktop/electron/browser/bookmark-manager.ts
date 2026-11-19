import { app } from 'electron';
import path from 'path';
import fs from 'fs';
import type { BookmarkItem } from '@ai-browser/shared';

export class BookmarkManager {
  private filePath: string;
  private bookmarks: BookmarkItem[] = [];

  constructor() {
    const userData = app?.getPath ? app.getPath('userData') : process.cwd();
    this.filePath = path.join(userData, 'browser_bookmarks.json');
    this.load();
  }

  private load() {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf-8');
        this.bookmarks = JSON.parse(raw);
      }
    } catch (e) {
      console.warn('Failed to load bookmarks:', e);
      this.bookmarks = [];
    }
  }

  private save() {
    try {
      fs.writeFileSync(this.filePath, JSON.stringify(this.bookmarks, null, 2), 'utf-8');
    } catch (e) {
      console.warn('Failed to save bookmarks:', e);
    }
  }

  public getBookmarks(): BookmarkItem[] {
    return this.bookmarks;
  }

  public isBookmarked(url: string): boolean {
    return this.bookmarks.some(b => b.url === url);
  }

  public addBookmark(params: { url: string; title: string; favicon?: string }): BookmarkItem {
    const existing = this.bookmarks.find(b => b.url === params.url);
    if (existing) {
      existing.title = params.title || existing.title;
      existing.favicon = params.favicon || existing.favicon;
      this.save();
      return existing;
    }

    const item: BookmarkItem = {
      id: `bm-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      url: params.url,
      title: params.title || params.url,
      favicon: params.favicon,
      createdAt: Date.now(),
    };

    this.bookmarks.unshift(item);
    this.save();
    return item;
  }

  public removeBookmark(urlOrId: string): boolean {
    const initialLen = this.bookmarks.length;
    this.bookmarks = this.bookmarks.filter(b => b.id !== urlOrId && b.url !== urlOrId);
    if (this.bookmarks.length !== initialLen) {
      this.save();
      return true;
    }
    return false;
  }
}
