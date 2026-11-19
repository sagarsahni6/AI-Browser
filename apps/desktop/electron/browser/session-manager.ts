import { app } from 'electron';
import path from 'path';
import fs from 'fs';
import type { BrowserSession } from '@ai-browser/shared';

export interface ClosedTabRecord {
  url: string;
  title: string;
  closedAt: number;
}

export class SessionManager {
  private filePath: string;
  private closedTabsStack: ClosedTabRecord[] = [];

  constructor() {
    const userData = app?.getPath ? app.getPath('userData') : process.cwd();
    this.filePath = path.join(userData, 'browser_session.json');
  }

  public recordClosedTab(url: string, title: string) {
    if (!url || url.startsWith('about:') || url === 'https://example.com') return;
    this.closedTabsStack.push({
      url,
      title: title || url,
      closedAt: Date.now(),
    });
    // Keep last 30 closed tabs
    if (this.closedTabsStack.length > 30) {
      this.closedTabsStack.shift();
    }
  }

  public popRecentlyClosedTab(): ClosedTabRecord | undefined {
    return this.closedTabsStack.pop();
  }

  public saveSession(tabs: Array<{ url: string; title: string }>, activeTabIndex = 0) {
    try {
      const validTabs = tabs.filter(t => t.url && !t.url.startsWith('chrome:'));
      if (validTabs.length === 0) return;

      const sessionData: BrowserSession = {
        tabs: validTabs,
        activeTabIndex,
        savedAt: Date.now(),
      };
      fs.writeFileSync(this.filePath, JSON.stringify(sessionData, null, 2), 'utf-8');
    } catch (e) {
      console.warn('Failed to save browser session:', e);
    }
  }

  public loadSession(): BrowserSession | null {
    try {
      if (fs.existsSync(this.filePath)) {
        const raw = fs.readFileSync(this.filePath, 'utf-8');
        return JSON.parse(raw);
      }
    } catch (e) {
      console.warn('Failed to load browser session:', e);
    }
    return null;
  }
}
