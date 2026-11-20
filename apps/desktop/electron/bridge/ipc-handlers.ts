import { ipcMain, type WebContentsView } from 'electron';
import { IPC_CHANNELS } from '@ai-browser/shared';
import type { TabManager } from '../browser/tab-manager';
import type { LayoutManager } from '../layout-manager';
import type { ProcessManager } from './process-manager';
import type { RpcClient } from './rpc-client';
import type { HistoryManager } from '../browser/history-manager';
import type { BookmarkManager } from '../browser/bookmark-manager';
import type { DownloadManager } from '../browser/download-manager';
import { SecretStorage } from '../security/secret-storage';
import { SenderValidator } from '../security/sender-validator';

export function setupIpcHandlers(deps: {
  tabManager: TabManager;
  layoutManager: LayoutManager;
  processManager: ProcessManager;
  rpcClient: RpcClient;
  historyManager: HistoryManager;
  bookmarkManager: BookmarkManager;
  downloadManager: DownloadManager;
  panelViews: WebContentsView[];
}) {
  const {
    tabManager,
    layoutManager,
    processManager,
    rpcClient,
    historyManager,
    bookmarkManager,
    downloadManager,
    panelViews
  } = deps;

  const broadcastToPanels = (channel: string, ...args: any[]) => {
    for (const view of panelViews) {
      if (!view.webContents.isDestroyed()) {
        view.webContents.send(channel, ...args);
      }
    }
  };

  // Subscribe TabManager changes and broadcast to all panels
  tabManager.subscribe((tabs, activeTabId) => {
    broadcastToPanels(IPC_CHANNELS.TAB_STATE_CHANGED, { tabs, activeTabId });
  });

  // Subscribe ProcessManager status changes
  processManager.on('status', (status) => {
    broadcastToPanels(IPC_CHANNELS.BACKEND_STATUS, status);
  });

  // Subscribe DownloadManager updates
  downloadManager.subscribe((item) => {
    broadcastToPanels(IPC_CHANNELS.DOWNLOAD_UPDATE, item);
  });

  // Forward AI chat streaming chunks to all panel views
  rpcClient.on('notification:chat:stream', (params: { chunk?: string }) => {
    if (params?.chunk) {
      broadcastToPanels(IPC_CHANNELS.CHAT_STREAM_CHUNK, params.chunk);
    }
  });

  // Forward AI chat actions to all panel views
  rpcClient.on('notification:chat:action', (params: any) => {
    broadcastToPanels(IPC_CHANNELS.CHAT_ACTION_UPDATE, params);
  });

  // Register JSON-RPC methods callable by Python process
  rpcClient.registerMethod('browser.get_tabs', async () => {
    return tabManager.getTabs();
  });

  rpcClient.registerMethod('browser.evaluate_js', async (params: { script: string }) => {
    const active = tabManager.getActiveTab();
    if (!active) return null;
    return await active.view.webContents.executeJavaScript(params.script);
  });

  rpcClient.registerMethod('browser.create_tab', async (params: { url?: string; is_private?: boolean }) => {
    return await tabManager.createTab(params?.url, params?.is_private);
  });

  rpcClient.registerMethod('browser.switch_tab', async (params: { tab_id?: string; tabId?: string }) => {
    const tid = params.tab_id || params.tabId;
    if (tid) tabManager.switchTab(tid);
    return true;
  });

  rpcClient.registerMethod('browser.close_tab', async (params: { tab_id?: string; tabId?: string }) => {
    const tid = params.tab_id || params.tabId;
    if (tid) tabManager.closeTab(tid);
    return true;
  });

  rpcClient.registerMethod('browser.navigate', async (params: { url: string }) => {
    tabManager.navigate(params.url);
    return true;
  });

  rpcClient.registerMethod('browser.inspect', async () => {
    return await tabManager.inspectActivePage();
  });

  rpcClient.registerMethod('browser.inspect_all_tabs', async () => {
    return await tabManager.inspectAllTabs();
  });

  rpcClient.registerMethod('browser.capture_screenshot', async () => {
    return await tabManager.captureActivePage();
  });

  rpcClient.registerMethod('browser.click', async (params: { x: number; y: number }) => {
    return await tabManager.clickAt(params.x, params.y);
  });

  rpcClient.registerMethod('browser.type', async (params: { text: string }) => {
    return await tabManager.typeText(params.text);
  });

  rpcClient.registerMethod('browser.fill', async (params: { x: number; y: number; text: string }) => {
    return await tabManager.fillInput(params.x, params.y, params.text);
  });

  rpcClient.registerMethod('browser.scroll', async (params: { delta_x: number; delta_y: number }) => {
    return await tabManager.scroll(params.delta_x, params.delta_y);
  });

  rpcClient.registerMethod('browser.press_key', async (params: { key: string }) => {
    return await tabManager.pressKey(params.key);
  });

  const secretStorage = new SecretStorage();

  ipcMain.handle(IPC_CHANNELS.SECRET_SET, async (event, key: string, value: string) => {
    if (!SenderValidator.isTrustedSender(event)) throw new Error('Untrusted IPC caller');
    secretStorage.setSecret(key, value);
  });

  ipcMain.handle(IPC_CHANNELS.SECRET_GET, async (event, key: string) => {
    if (!SenderValidator.isTrustedSender(event)) throw new Error('Untrusted IPC caller');
    return secretStorage.getSecret(key);
  });

  // Renderer IPC Handlers
  ipcMain.handle(IPC_CHANNELS.TABS_GET, async () => {
    return tabManager.getTabs();
  });

  ipcMain.handle(IPC_CHANNELS.TAB_CREATE, async (_event, url?: string, isPrivate?: boolean) => {
    return await tabManager.createTab(url, isPrivate);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_CLOSE, async (_event, tabId: string) => {
    tabManager.closeTab(tabId);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_SWITCH, async (_event, tabId: string) => {
    tabManager.switchTab(tabId);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_RESTORE_CLOSED, async () => {
    return tabManager.restoreClosedTab();
  });

  ipcMain.handle(IPC_CHANNELS.TAB_DUPLICATE, async (_event, tabId: string) => {
    tabManager.duplicateTab(tabId);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_SET_PINNED, async (_event, tabId: string, isPinned: boolean) => {
    tabManager.setTabPinned(tabId, isPinned);
  });

  ipcMain.handle(IPC_CHANNELS.NAV_NAVIGATE, async (_event, url: string) => {
    tabManager.navigate(url);
  });

  ipcMain.handle(IPC_CHANNELS.NAV_BACK, async () => {
    tabManager.goBack();
  });

  ipcMain.handle(IPC_CHANNELS.NAV_FORWARD, async () => {
    tabManager.goForward();
  });

  ipcMain.handle(IPC_CHANNELS.NAV_RELOAD, async () => {
    tabManager.reload();
  });

  ipcMain.handle(IPC_CHANNELS.NAV_STOP, async () => {
    tabManager.stop();
  });

  // History Handlers
  ipcMain.handle(IPC_CHANNELS.HISTORY_GET, async (_event, limit?: number) => {
    return historyManager.getHistory(limit);
  });

  ipcMain.handle(IPC_CHANNELS.HISTORY_SEARCH, async (_event, query: string) => {
    return historyManager.search(query);
  });

  ipcMain.handle(IPC_CHANNELS.HISTORY_CLEAR, async () => {
    historyManager.clear();
  });

  // Bookmark Handlers
  ipcMain.handle(IPC_CHANNELS.BOOKMARKS_GET, async () => {
    return bookmarkManager.getBookmarks();
  });

  ipcMain.handle(IPC_CHANNELS.BOOKMARK_ADD, async (_event, item: { url: string; title: string; favicon?: string }) => {
    return bookmarkManager.addBookmark(item);
  });

  ipcMain.handle(IPC_CHANNELS.BOOKMARK_REMOVE, async (_event, urlOrId: string) => {
    return bookmarkManager.removeBookmark(urlOrId);
  });

  ipcMain.handle(IPC_CHANNELS.BOOKMARK_IS_SAVED, async (_event, url: string) => {
    return bookmarkManager.isBookmarked(url);
  });

  // Download Handlers
  ipcMain.handle(IPC_CHANNELS.DOWNLOADS_GET, async () => {
    return downloadManager.getDownloads();
  });

  ipcMain.handle(IPC_CHANNELS.DOWNLOAD_OPEN_FILE, async (_event, id: string) => {
    return await downloadManager.openFile(id);
  });

  ipcMain.handle(IPC_CHANNELS.DOWNLOAD_OPEN_FOLDER, async (_event, id: string) => {
    return downloadManager.openFolder(id);
  });

  // Layout & UI Handlers
  ipcMain.handle(IPC_CHANNELS.PANEL_TOGGLE_SIDEBAR, async () => {
    return layoutManager.toggleSidebar();
  });

  ipcMain.handle(IPC_CHANNELS.PANEL_TOGGLE_ASSISTANT, async () => {
    return layoutManager.toggleAssistant();
  });

  ipcMain.handle(IPC_CHANNELS.GET_INITIAL_STATE, async () => {
    return {
      tabs: tabManager.getTabs(),
      activeTabId: tabManager.getActiveTabId(),
      sidebarOpen: layoutManager.isSidebarOpen(),
      assistantOpen: layoutManager.isAssistantOpen(),
      backendStatus: processManager.getStatus(),
    };
  });

  ipcMain.handle(IPC_CHANNELS.CAPTURE_PAGE, async () => {
    return await tabManager.captureActivePage();
  });

  ipcMain.handle(IPC_CHANNELS.INSPECT_PAGE, async () => {
    return await tabManager.inspectActivePage();
  });

  ipcMain.handle(IPC_CHANNELS.STOP_ASSISTANT, async () => {
    if (processManager.getStatus().online) {
      try {
        return await rpcClient.call('assistant.stop', {});
      } catch (e) {
        return false;
      }
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.SEND_CHAT_MESSAGE, async (_event, { message, context }) => {
    if (processManager.getStatus().online) {
      try {
        const sanitizeString = (str?: string): string => {
          if (!str) return '';
          return typeof (str as any).toWellFormed === 'function'
            ? (str as any).toWellFormed()
            : str.replace(/[\uD800-\uDFFF]/g, '');
        };

        const cleanMessage = sanitizeString(message);
        const enrichedContext: Record<string, any> = { ...(context || {}) };
        if (!enrichedContext.visibleText && tabManager.getActiveTab()) {
          try {
            const obs = await tabManager.inspectActivePage();
            if (obs) {
              enrichedContext.title = sanitizeString(obs.title);
              enrichedContext.url = sanitizeString(obs.url);
              if (obs.visibleText) {
                enrichedContext.visibleText = sanitizeString(obs.visibleText).slice(0, 4000);
              }
            }
          } catch (e) {
            // CDP inspect fallback
          }
        }
        const response = await rpcClient.call('assistant.chat', { message: cleanMessage, context: enrichedContext });
        return response?.reply || 'Assistant processed request.';
      } catch (err: any) {
        return `Backend communication error: ${err.message}`;
      }
    } else {
      return `Backend is offline. Running in standalone local browser mode.`;
    }
  });

  // Task & Multi-Agent Operations
  ipcMain.handle(IPC_CHANNELS.TASK_CREATE, async (_event, payload: { title: string; prompt: string; engine?: string; provider?: string; model?: string; mode?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.create', payload);
    }
    return { error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.TASKS_LIST, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.list', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.TASK_GET, async (_event, taskId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.get', { task_id: taskId });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_CANCEL, async (_event, taskId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.cancel', { task_id: taskId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_APPROVE, async (_event, taskId: string, decision: boolean = true) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.approve', { task_id: taskId, decision });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_REJECT, async (_event, taskId: string, reason?: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.reject', { task_id: taskId, reason });
    }
    return false;
  });

  // Research Collections
  ipcMain.handle(IPC_CHANNELS.COLLECTIONS_LIST, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('collections.list', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.COLLECTION_CREATE, async (_event, { name, description }: { name: string; description?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('collections.create', { name, description });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.COLLECTION_DELETE, async (_event, id: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('collections.delete', { id });
    }
    return false;
  });
}
