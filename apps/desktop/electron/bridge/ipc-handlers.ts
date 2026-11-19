import { ipcMain, type WebContentsView } from 'electron';
import { IPC_CHANNELS } from '@ai-browser/shared';
import type { TabManager } from '../browser/tab-manager';
import type { LayoutManager } from '../layout-manager';
import type { ProcessManager } from './process-manager';
import type { RpcClient } from './rpc-client';

export function setupIpcHandlers(deps: {
  tabManager: TabManager;
  layoutManager: LayoutManager;
  processManager: ProcessManager;
  rpcClient: RpcClient;
  panelViews: WebContentsView[];
}) {
  const { tabManager, layoutManager, processManager, rpcClient, panelViews } = deps;

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

  // Register JSON-RPC methods callable by Python process
  rpcClient.registerMethod('browser.get_tabs', async () => {
    return tabManager.getTabs();
  });

  rpcClient.registerMethod('browser.create_tab', async (params: { url?: string }) => {
    return await tabManager.createTab(params?.url);
  });

  rpcClient.registerMethod('browser.switch_tab', async (params: { tab_id: string }) => {
    tabManager.switchTab(params.tab_id);
    return true;
  });

  rpcClient.registerMethod('browser.close_tab', async (params: { tab_id: string }) => {
    tabManager.closeTab(params.tab_id);
    return true;
  });

  rpcClient.registerMethod('browser.navigate', async (params: { url: string }) => {
    tabManager.navigate(params.url);
    return true;
  });

  rpcClient.registerMethod('browser.inspect', async () => {
    return await tabManager.inspectActivePage();
  });

  rpcClient.registerMethod('browser.capture_screenshot', async () => {
    return await tabManager.captureActivePage();
  });

  // Renderer IPC Handlers
  ipcMain.handle(IPC_CHANNELS.TABS_GET, async () => {
    return tabManager.getTabs();
  });

  ipcMain.handle(IPC_CHANNELS.TAB_CREATE, async (_event, url?: string) => {
    return await tabManager.createTab(url);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_CLOSE, async (_event, tabId: string) => {
    tabManager.closeTab(tabId);
  });

  ipcMain.handle(IPC_CHANNELS.TAB_SWITCH, async (_event, tabId: string) => {
    tabManager.switchTab(tabId);
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

  ipcMain.handle(IPC_CHANNELS.SEND_CHAT_MESSAGE, async (_event, { message, context }) => {
    // If Python backend is connected, route via RPC or HTTP
    if (processManager.getStatus().online) {
      try {
        const response = await rpcClient.call('assistant.chat', { message, context });
        return response?.reply || 'Assistant processed request.';
      } catch (err: any) {
        return `Backend communication error: ${err.message}`;
      }
    } else {
      return `Backend is offline. Running in standalone local browser mode.`;
    }
  });
}
