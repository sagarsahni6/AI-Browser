import { WebContentsView, type BaseWindow } from 'electron';
import type { BrowserTab, PageObservation } from '@ai-browser/shared';
import { DebuggerManager } from './debugger-manager';
import { PageObserver } from './page-observer';
import { ScreenshotManager } from './screenshot-manager';
import { PageActions } from './page-actions';
import { HistoryManager } from './history-manager';
import { SessionManager } from './session-manager';
import { attachContextMenu } from './context-menu';
import { registerShortcuts } from './keyboard-shortcuts';
import { generateErrorPageHtml } from './error-page';
import { getPanelUrl } from '../panels/panel-factory';

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
  private historyManager: HistoryManager;
  private sessionManager: SessionManager;
  private listeners: Set<TabStateListener> = new Set();
  private onActiveTabChanged?: (tabView: WebContentsView | null) => void;
  private onToggleSidebar?: () => void;
  private onToggleAssistant?: () => void;
  private onBookmarkPage?: (url: string, title: string) => void;
  private onAskAI?: (text: string) => void;
  private onOpenCommandPalette?: () => void;

  constructor(
    baseWindow: BaseWindow,
    debuggerManager: DebuggerManager,
    historyManager: HistoryManager,
    sessionManager: SessionManager
  ) {
    this.baseWindow = baseWindow;
    this.debuggerManager = debuggerManager;
    this.historyManager = historyManager;
    this.sessionManager = sessionManager;
  }

  public setCallbacks(cb: {
    onActiveTabChanged?: (tabView: WebContentsView | null) => void;
    onToggleSidebar?: () => void;
    onToggleAssistant?: () => void;
    onBookmarkPage?: (url: string, title: string) => void;
    onAskAI?: (text: string) => void;
    onOpenCommandPalette?: () => void;
  }) {
    if (cb.onActiveTabChanged) this.onActiveTabChanged = cb.onActiveTabChanged;
    if (cb.onToggleSidebar) this.onToggleSidebar = cb.onToggleSidebar;
    if (cb.onToggleAssistant) this.onToggleAssistant = cb.onToggleAssistant;
    if (cb.onBookmarkPage) this.onBookmarkPage = cb.onBookmarkPage;
    if (cb.onAskAI) this.onAskAI = cb.onAskAI;
    if (cb.onOpenCommandPalette) this.onOpenCommandPalette = cb.onOpenCommandPalette;
  }

  public setOnActiveTabChanged(callback: (tabView: WebContentsView | null) => void) {
    this.setCallbacks({ onActiveTabChanged: callback });
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
    // Automatically save session state
    this.sessionManager.saveSession(
      tabList.map(t => ({ url: t.url, title: t.title })),
      Math.max(0, tabList.findIndex(t => t.id === this.activeTabId))
    );
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

  public async createTab(initialUrl = '', isPrivate = false): Promise<string> {
    const id = `tab-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    const effectiveUrl = (!initialUrl || initialUrl === 'ai://newtab' || initialUrl === 'https://example.com')
      ? getPanelUrl('newtab')
      : initialUrl;

    const partition = isPrivate ? `partition:incognito-${Date.now()}` : 'persist:default';

    const view = new WebContentsView({
      webPreferences: {
        partition,
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
      isPrivate,
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

      // Add to history if not in private mode and valid web url
      if (!isPrivate && info.url && !info.url.startsWith('data:') && !info.url.startsWith('about:')) {
        this.historyManager.addEntry(info.url, info.title, false);
      }

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

    wc.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
      if (errorCode === -3) return; // Ignore aborted requests
      console.warn(`[Tab] Failed to load ${validatedURL}: ${errorCode} (${errorDescription})`);
      const errorPageDataUrl = generateErrorPageHtml(validatedURL, errorCode, errorDescription);
      wc.loadURL(errorPageDataUrl);
    });

    // Intercept window.open, target="_blank", and OAuth popups: open as tabs inside AI Browser
    wc.setWindowOpenHandler((details) => {
      const targetUrl = details.url;
      if (targetUrl && targetUrl !== 'about:blank') {
        this.createTab(targetUrl, isPrivate);
      }
      return { action: 'deny' };
    });

    // Handle tab self-close when in-page script calls window.close()
    wc.on('close', () => {
      this.closeTab(id);
    });

    // Attach Context Menu
    attachContextMenu(wc, {
      onBookmarkPage: (url, title) => this.onBookmarkPage?.(url, title),
      onAskAI: (text) => this.onAskAI?.(text),
    });

    // Register Keyboard Shortcuts
    registerShortcuts(wc, {
      onNewTab: () => this.createTab(),
      onCloseTab: () => this.closeTab(this.activeTabId),
      onReload: () => this.reload(),
      onRestoreClosedTab: () => this.restoreClosedTab(),
      onGoBack: () => this.goBack(),
      onGoForward: () => this.goForward(),
      onNextTab: () => this.cycleTab(1),
      onPrevTab: () => this.cycleTab(-1),
      onToggleSidebar: () => this.onToggleSidebar?.(),
      onToggleAssistant: () => this.onToggleAssistant?.(),
      onOpenCommandPalette: () => this.onOpenCommandPalette?.(),
    });

    this.baseWindow.contentView.addChildView(view);
    view.webContents.loadURL(effectiveUrl);
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

    // Record in closed tabs stack
    if (!tabItem.info.isPrivate) {
      this.sessionManager.recordClosedTab(tabItem.info.url, tabItem.info.title);
    }

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

  public restoreClosedTab(): string | null {
    const closed = this.sessionManager.popRecentlyClosedTab();
    if (closed && closed.url) {
      this.createTab(closed.url);
      return closed.url;
    }
    return null;
  }

  public setTabPinned(tabId: string, isPinned: boolean): void {
    const item = this.tabs.get(tabId);
    if (item) {
      item.info.isPinned = isPinned;
      this.notify();
    }
  }

  public closeOtherTabs(keepTabId: string): void {
    const toClose = Array.from(this.tabs.keys()).filter(id => id !== keepTabId);
    for (const id of toClose) {
      const item = this.tabs.get(id);
      if (item && !item.info.isPinned) {
        this.closeTab(id);
      }
    }
  }

  public duplicateTab(tabId: string): void {
    const item = this.tabs.get(tabId);
    if (item && item.info.url) {
      this.createTab(item.info.url, item.info.isPrivate);
    }
  }

  public cycleTab(direction: 1 | -1): void {
    const tabIds = Array.from(this.tabs.keys());
    if (tabIds.length <= 1) return;

    const currentIdx = tabIds.indexOf(this.activeTabId);
    const nextIdx = (currentIdx + direction + tabIds.length) % tabIds.length;
    this.switchTab(tabIds[nextIdx]);
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

  public async inspectAllTabs(): Promise<PageObservation[]> {
    const results: PageObservation[] = [];
    for (const [id, item] of this.tabs.entries()) {
      try {
        if (!item.view.webContents.isDestroyed()) {
          const cdp = this.debuggerManager.getClient(item.view.webContents);
          const observer = new PageObserver(item.view.webContents, cdp);
          const obs = await observer.observe(id);
          results.push(obs);
        }
      } catch (err) {
        console.warn(`Failed to inspect tab ${id}:`, err);
      }
    }
    return results;
  }

  public async clickAt(x: number, y: number): Promise<boolean> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const actions = new PageActions(cdp);
    return actions.click(x, y);
  }

  public async typeText(text: string): Promise<boolean> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const actions = new PageActions(cdp);
    return actions.typeText(text);
  }

  public async fillInput(x: number, y: number, text: string): Promise<boolean> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const actions = new PageActions(cdp);
    return actions.fillInput(x, y, text);
  }

  public async scroll(deltaX: number, deltaY: number): Promise<boolean> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const actions = new PageActions(cdp);
    return actions.scrollPage(deltaX, deltaY);
  }

  public async pressKey(key: string): Promise<boolean> {
    const active = this.getActiveTab();
    if (!active) throw new Error('No active tab');
    const cdp = this.debuggerManager.getClient(active.view.webContents);
    const actions = new PageActions(cdp);
    return actions.pressKey(key);
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
