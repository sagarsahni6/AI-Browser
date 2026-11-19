import { WebContentsView, type BaseWindow } from 'electron';
import type { BrowserTab, PageObservation } from '@ai-browser/shared';
import { DebuggerManager } from './debugger-manager';
import { PageObserver } from './page-observer';
import { ScreenshotManager } from './screenshot-manager';

export interface TabItem {
  id: string;
  view: WebContentsView;
  info: BrowserTab;
}

export type TabStateListener = (tabs: BrowserTab[], activeTabId: string) => void;

export class TabManager {
  private baseWindow: BaseWindow;
  private tabs: Map<string, TabItem> = new Map();
  private activeTabId: string = '';
  private debuggerManager: DebuggerManager;
  private listeners: Set<TabStateListener> = new Set();
  private onActiveTabChanged?: (tabView: WebContentsView | null) => void;

  constructor(baseWindow: BaseWindow, debuggerManager: DebuggerManager) {
    this.baseWindow = baseWindow;
    this.debuggerManager = debuggerManager;
  }

  public setOnActiveTabChanged(callback: (tabView: WebContentsView | null) => void) {
    this.onActiveTabChanged = callback;
  }

  public subscribe(listener: TabStateListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    const tabList = Array.from(this.tabs.values()).map(t => t.info);
    for (const listener of this.listeners) {
      listener(tabList, this.activeTabId);
    }
  }

  public getTabs(): BrowserTab[] {
    return Array.from(this.tabs.values()).map(t => t.info);
  }

  public getActiveTabId(): string {
    return this.activeTabId;
  }

  public getActiveTab(): TabItem | undefined {
    return this.tabs.get(this.activeTabId);
  }

  private canGoBack(wc: any): boolean {
    if (wc.navigationHistory?.canGoBack) return wc.navigationHistory.canGoBack();
    return wc.canGoBack ? wc.canGoBack() : false;
  }

  private canGoForward(wc: any): boolean {
    if (wc.navigationHistory?.canGoForward) return wc.navigationHistory.canGoForward();
    return wc.canGoForward ? wc.canGoForward() : false;
  }

  public async createTab(initialUrl = 'https://example.com'): Promise<string> {
    const id = `tab-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;

    const view = new WebContentsView({
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        webSecurity: true,
        allowRunningInsecureContent: false,
      }
    });

    const info: BrowserTab = {
      id,
      url: initialUrl,
      title: 'New Tab',
      isLoading: true,
      canGoBack: false,
      canGoForward: false,
    };

    const tabItem: TabItem = { id, view, info };
    this.tabs.set(id, tabItem);

    const wc = view.webContents;

    wc.on('did-start-loading', () => {
      info.isLoading = true;
      this.notify();
    });

    wc.on('did-stop-loading', () => {
      info.isLoading = false;
      info.canGoBack = this.canGoBack(wc);
      info.canGoForward = this.canGoForward(wc);
      info.url = wc.getURL();
      info.title = wc.getTitle() || info.title;
      this.notify();
    });

    wc.on('page-title-updated', (_event, title) => {
      info.title = title;
      this.notify();
    });

    wc.on('page-favicon-updated', (_event, favicons) => {
      if (favicons.length > 0) {
        info.favicon = favicons[0];
        this.notify();
      }
    });

    wc.on('did-navigate', (_event, url) => {
      info.url = url;
      info.canGoBack = this.canGoBack(wc);
      info.canGoForward = this.canGoForward(wc);
      this.notify();
    });

    this.baseWindow.contentView.addChildView(view);
    view.webContents.loadURL(initialUrl);
    this.switchTab(id);

    return id;
  }

  public switchTab(tabId: string): void {
    const target = this.tabs.get(tabId);
    if (!target) return;

    this.activeTabId = tabId;

    for (const [id, item] of this.tabs.entries()) {
      if (id === tabId) {
        if (this.onActiveTabChanged) {
          this.onActiveTabChanged(item.view);
        }
      } else {
        if (!item.view.webContents.isDestroyed()) {
          item.view.setBounds({ x: 0, y: 0, width: 0, height: 0 });
        }
      }
    }

    this.notify();
  }

  public closeTab(tabId: string): void {
    const tabItem = this.tabs.get(tabId);
    if (!tabItem) return;

    this.debuggerManager.removeClient(tabItem.view.webContents.id);

    try {
      this.baseWindow.contentView.removeChildView(tabItem.view);
    } catch (e) {
      console.warn('Error removing child view:', e);
    }

    if (!tabItem.view.webContents.isDestroyed()) {
      (tabItem.view.webContents as any).close?.();
    }

    this.tabs.delete(tabId);

    if (this.activeTabId === tabId) {
      const remaining = Array.from(this.tabs.keys());
      if (remaining.length > 0) {
        this.switchTab(remaining[remaining.length - 1]);
      } else {
        this.createTab();
      }
    } else {
      this.notify();
    }
  }

  public navigate(url: string): void {
    const active = this.getActiveTab();
    if (!active || active.view.webContents.isDestroyed()) return;
    active.view.webContents.loadURL(url);
  }

  public goBack(): void {
    const active = this.getActiveTab();
    if (active && this.canGoBack(active.view.webContents)) {
      active.view.webContents.goBack();
    }
  }

  public goForward(): void {
    const active = this.getActiveTab();
    if (active && this.canGoForward(active.view.webContents)) {
      active.view.webContents.goForward();
    }
  }

  public reload(): void {
    const active = this.getActiveTab();
    if (active) {
      active.view.webContents.reload();
    }
  }

  public stop(): void {
    const active = this.getActiveTab();
    if (active) {
      active.view.webContents.stop();
    }
  }

  public async captureActivePage(): Promise<string> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab to capture');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    return ScreenshotManager.capture(active.view.webContents, cdp);
  }

  public async inspectActivePage(): Promise<PageObservation> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab to inspect');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const observer = new PageObserver(active.view.webContents, cdp);
    return observer.observe(active.id);
  }

  public dispose(): void {
    for (const [id, item] of this.tabs.entries()) {
      this.debuggerManager.removeClient(item.view.webContents.id);
      try {
        this.baseWindow.contentView.removeChildView(item.view);
      } catch (e) { /* ignore */ }
    }
    this.tabs.clear();
  }
}
