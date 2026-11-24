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
        try {
          view.webContents.send(channel, ...args);
        } catch {
          // Ignore transient webContents frame disposal during navigation
        }
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
      if (!layoutManager.isAssistantOpen()) {
        const res = layoutManager.setAssistantOpen(true);
        broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
      }
      broadcastToPanels(IPC_CHANNELS.CHAT_STREAM_CHUNK, params.chunk);
    }
  });

  // Forward AI chat actions to all panel views
  rpcClient.on('notification:chat:action', (params: any) => {
    if (!layoutManager.isAssistantOpen()) {
      const res = layoutManager.setAssistantOpen(true);
      broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    }
    broadcastToPanels(IPC_CHANNELS.CHAT_ACTION_UPDATE, params);
    if (params?.status === 'approval_required') {
      broadcastToPanels(IPC_CHANNELS.APPROVAL_REQUEST, params);
    }
  });

  // Forward task step updates to all panel views
  rpcClient.on('notification:task:step_updated', (params: any) => {
    if (!layoutManager.isAssistantOpen()) {
      const res = layoutManager.setAssistantOpen(true);
      broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    }
    broadcastToPanels(IPC_CHANNELS.TASK_STEP_UPDATED, params);
    if (params?.status === 'approval_required') {
      broadcastToPanels(IPC_CHANNELS.APPROVAL_REQUEST, params);
    }
  });

  // Forward workflow step updates to all panel views
  rpcClient.on('notification:workflow:step_updated', (params: any) => {
    broadcastToPanels(IPC_CHANNELS.WORKFLOW_STEP_UPDATE, params);
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

  const emitLaserIndicator = (coords: { x: number; y: number }) => {
    const activeTab = tabManager.getActiveTab();
    if (activeTab && !activeTab.view.webContents.isDestroyed()) {
      activeTab.view.webContents.send(IPC_CHANNELS.COMET_LASER_INDICATOR, coords);
      activeTab.view.webContents.executeJavaScript(`
        (() => {
          const dot = document.createElement('div');
          dot.style.position = 'fixed';
          dot.style.left = '${coords.x}px';
          dot.style.top = '${coords.y}px';
          dot.style.width = '18px';
          dot.style.height = '18px';
          dot.style.borderRadius = '50%';
          dot.style.backgroundColor = 'rgba(239, 68, 68, 0.85)';
          dot.style.boxShadow = '0 0 16px rgba(239, 68, 68, 1)';
          dot.style.transform = 'translate(-50%, -50%) scale(1)';
          dot.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
          dot.style.pointerEvents = 'none';
          dot.style.zIndex = '2147483647';
          document.body.appendChild(dot);
          requestAnimationFrame(() => {
            dot.style.transform = 'translate(-50%, -50%) scale(2.8)';
            dot.style.opacity = '0';
          });
          setTimeout(() => dot.remove(), 700);
        })()
      `).catch(() => {});
    }
    broadcastToPanels(IPC_CHANNELS.COMET_LASER_INDICATOR, coords);
  };

  rpcClient.registerMethod('browser.click', async (params: { x: number; y: number }) => {
    const success = await tabManager.clickAt(params.x, params.y);
    if (success) {
      emitLaserIndicator({ x: params.x, y: params.y });
    }
    return { success: Boolean(success), x: params.x, y: params.y };
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

  rpcClient.registerMethod('browser.click_selector', async (params: { selector: string }) => {
    const res = await tabManager.clickSelector(params.selector);
    if (res && res.success && typeof res.x === 'number' && typeof res.y === 'number') {
      emitLaserIndicator({ x: res.x, y: res.y });
    }
    return res;
  });

  rpcClient.registerMethod('browser.fill_selector', async (params: { selector: string; text: string }) => {
    return await tabManager.fillSelector(params.selector, params.text);
  });

  rpcClient.registerMethod('browser.wait_for_selector', async (params: { selector: string; timeout_ms?: number }) => {
    return await tabManager.waitForSelector(params.selector, params.timeout_ms);
  });

  rpcClient.registerMethod('browser.detect_forms', async () => {
    return await tabManager.detectForms();
  });

  rpcClient.registerMethod('browser.get_accessibility_tree', async () => {
    return await tabManager.getAccessibilityTree();
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
    const res = layoutManager.toggleSidebar();
    broadcastToPanels(IPC_CHANNELS.PANEL_SIDEBAR_STATE_CHANGED, res);
    return res;
  });

  ipcMain.handle(IPC_CHANNELS.PANEL_SET_SIDEBAR_OPEN, async (_event, open: boolean) => {
    const res = layoutManager.setSidebarOpen(open);
    broadcastToPanels(IPC_CHANNELS.PANEL_SIDEBAR_STATE_CHANGED, res);
    return res;
  });

  ipcMain.handle(IPC_CHANNELS.PANEL_TOGGLE_ASSISTANT, async () => {
    const res = layoutManager.toggleAssistant();
    broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    return res;
  });

  ipcMain.handle(IPC_CHANNELS.PANEL_SET_ASSISTANT_OPEN, async (_event, open: boolean) => {
    const res = layoutManager.setAssistantOpen(open);
    broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    return res;
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
    if (!layoutManager.isAssistantOpen()) {
      const res = layoutManager.setAssistantOpen(true);
      broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    }
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
        if ((!enrichedContext.visibleText || !enrichedContext.interactiveElements) && tabManager.getActiveTab()) {
          try {
            const obs = await tabManager.inspectActivePage();
            if (obs) {
              if (!enrichedContext.title) enrichedContext.title = sanitizeString(obs.title);
              if (!enrichedContext.url) enrichedContext.url = sanitizeString(obs.url);
              if (obs.metaDescription) {
                enrichedContext.metaDescription = sanitizeString(obs.metaDescription);
              }
              if (!enrichedContext.visibleText && obs.visibleText) {
                enrichedContext.visibleText = sanitizeString(obs.visibleText).slice(0, 4000);
              }
              if (obs.interactiveElements && Array.isArray(obs.interactiveElements)) {
                enrichedContext.interactiveElements = obs.interactiveElements.slice(0, 30);
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
    if (!layoutManager.isAssistantOpen()) {
      const res = layoutManager.setAssistantOpen(true);
      broadcastToPanels(IPC_CHANNELS.PANEL_ASSISTANT_STATE_CHANGED, res);
    }
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

  ipcMain.handle(IPC_CHANNELS.TASK_PAUSE, async (_event, taskId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.pause', { task_id: taskId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_RESUME, async (_event, taskId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.resume', { task_id: taskId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_APPROVE, async (_event, taskId: string, decision: boolean = true, approvalId?: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.approve', { task_id: taskId, decision, approval_id: approvalId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.TASK_REJECT, async (_event, taskId: string, reason?: string, approvalId?: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('tasks.reject', { task_id: taskId, reason, approval_id: approvalId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.APPROVAL_RESPONSE, async (_event, payload: { taskId: string; approved: boolean; reason?: string }) => {
    if (processManager.getStatus().online) {
      if (payload.approved) {
        return await rpcClient.call('tasks.approve', { task_id: payload.taskId, decision: true });
      } else {
        return await rpcClient.call('tasks.reject', { task_id: payload.taskId, reason: payload.reason });
      }
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

  // Workflow Handlers
  ipcMain.handle(IPC_CHANNELS.WORKFLOWS_LIST, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.list', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_GET, async (_event, workflowId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.get', { workflow_id: workflowId });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_SAVE, async (_event, data: { name: string; description?: string; steps: any[]; variables?: any; id?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.save', data);
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_DELETE, async (_event, workflowId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.delete', { workflow_id: workflowId });
    }
    return false;
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_EXECUTE, async (_event, workflowId: string, variables?: Record<string, any>) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.execute', { workflow_id: workflowId, variables });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_EXPORT, async (_event, workflowId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.export', { workflow_id: workflowId });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_IMPORT, async (_event, data: any) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('workflows.import', { data });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_RECORD_START, async () => {
    return await tabManager.startWorkflowRecording();
  });

  ipcMain.handle(IPC_CHANNELS.WORKFLOW_RECORD_STOP, async () => {
    return await tabManager.stopWorkflowRecording();
  });

  // Research & Document Intelligence + Data Extraction
  ipcMain.handle(IPC_CHANNELS.RESEARCH_SYNTHESIZE, async (_event, params: { topic: string; sources?: string[]; depth?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('research.synthesize', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.RESEARCH_LIST_REPORTS, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('research.list_reports', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.RESEARCH_GET_REPORT, async (_event, reportId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('research.get_report', { report_id: reportId });
    }
    return null;
  });

  ipcMain.handle(IPC_CHANNELS.RESEARCH_DELETE_REPORT, async (_event, reportId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('research.delete_report', { report_id: reportId });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DOCUMENTS_READ_PDF, async (_event, params: { path_or_url: string; max_pages?: number }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('documents.read_pdf', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DOCUMENTS_SUMMARIZE_PDF, async (_event, params: { path_or_url: string; query?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('documents.summarize_pdf', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DATA_EXTRACT_TABLE, async (_event, params: { selector?: string; pagination_next_selector?: string; max_pages?: number }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('data.extract_table', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DATA_EXPORT, async (_event, params: { data: any[]; format?: string; filename?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('data.export', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  // Long-Term Memory
  ipcMain.handle(IPC_CHANNELS.MEMORY_REMEMBER, async (_event, params: { key: string; value: string; category?: string; tags?: string[] }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('memory.remember', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.MEMORY_RECALL, async (_event, params: { query: string; category?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('memory.recall', params);
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.MEMORY_GET_ALL, async (_event, category?: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('memory.get_all', { category });
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.MEMORY_FORGET, async (_event, memoryId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('memory.forget', { memory_id: memoryId });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  // Website Monitors
  ipcMain.handle(IPC_CHANNELS.MONITORS_CREATE, async (_event, params: { url: string; name: string; selector?: string; check_interval?: number }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('monitors.create', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.MONITORS_LIST, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('monitors.list', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.MONITORS_CHECK_NOW, async (_event, monitorId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('monitors.check_now', { monitor_id: monitorId });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.MONITORS_DELETE, async (_event, monitorId: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('monitors.delete', { monitor_id: monitorId });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  // Windows Desktop Automation
  ipcMain.handle(IPC_CHANNELS.DESKTOP_CLICK, async (_event, params: { x: number; y: number; button?: string }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.click', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_TYPE, async (_event, text: string) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.type', { text });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_HOTKEY, async (_event, keys: string[]) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.hotkey', { keys });
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_CAPTURE_SCREEN, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.capture_screen', {});
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_LAUNCH_APP, async (_event, params: { app_name: string; args?: string[] }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.launch_app', params);
    }
    return { status: 'error', error: 'Backend offline' };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_EMERGENCY_STOP, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.emergency_stop', {});
    }
    return { status: 'ok', emergency_stopped: true };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_RESET_STOP, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.reset_stop', {});
    }
    return { status: 'ok', emergency_stopped: false };
  });

  ipcMain.handle(IPC_CHANNELS.DESKTOP_GET_AUDIT_LOGS, async (_event, limit?: number) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('desktop.get_audit_logs', { limit: limit || 100 });
    }
    return [];
  });

  // Agent Skills System
  ipcMain.handle(IPC_CHANNELS.SKILLS_LIST, async () => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('skills.list', {});
    }
    return [];
  });

  ipcMain.handle(IPC_CHANNELS.SKILLS_TOGGLE, async (_event, skillId: string, enabled?: boolean) => {
    if (processManager.getStatus().online) {
      const res = await rpcClient.call('skills.toggle', { skill_id: skillId, enabled });
      broadcastToPanels(IPC_CHANNELS.SKILLS_CHANGED, res);
      return res;
    }
    return { skill_id: skillId, enabled: false };
  });

  ipcMain.handle(IPC_CHANNELS.SKILLS_EXECUTE, async (_event, payload: { toolName: string; params?: any }) => {
    if (processManager.getStatus().online) {
      return await rpcClient.call('skills.execute', { tool_name: payload.toolName, params: payload.params || {} });
    }
    return { status: 'error', error: 'Backend offline' };
  });
}
