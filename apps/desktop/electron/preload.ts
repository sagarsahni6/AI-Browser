import { contextBridge, ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@ai-browser/shared';
import type { BrowserTab, PageObservation } from '@ai-browser/shared';

const electronAPI = {
  // Tabs
  createTab: (url?: string): Promise<string> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_CREATE, url);
  },
  closeTab: (tabId: string): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_CLOSE, tabId);
  },
  switchTab: (tabId: string): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_SWITCH, tabId);
  },
  getTabs: (): Promise<BrowserTab[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TABS_GET);
  },
  onTabsUpdated: (callback: (tabs: BrowserTab[], activeTabId: string) => void) => {
    const handler = (_event: unknown, data: { tabs: BrowserTab[]; activeTabId: string }) => {
      callback(data.tabs, data.activeTabId);
    };
    ipcRenderer.on(IPC_CHANNELS.TAB_STATE_CHANGED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.TAB_STATE_CHANGED, handler);
    };
  },

  // Navigation
  navigate: (url: string): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.NAV_NAVIGATE, url);
  },
  goBack: (): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.NAV_BACK);
  },
  goForward: (): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.NAV_FORWARD);
  },
  reload: (): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.NAV_RELOAD);
  },
  stop: (): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.NAV_STOP);
  },

  // Panels & Window
  toggleSidebar: (): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.PANEL_TOGGLE_SIDEBAR);
  },
  toggleAssistant: (): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.PANEL_TOGGLE_ASSISTANT);
  },
  getInitialState: (): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.GET_INITIAL_STATE);
  },

  // Browser Actions & CDP
  capturePage: (): Promise<string> => {
    return ipcRenderer.invoke(IPC_CHANNELS.CAPTURE_PAGE);
  },
  inspectPage: (): Promise<PageObservation> => {
    return ipcRenderer.invoke(IPC_CHANNELS.INSPECT_PAGE);
  },

  // Backend state
  onBackendStatus: (callback: (status: { online: boolean; port?: number }) => void) => {
    const handler = (_event: unknown, status: { online: boolean; port?: number }) => {
      callback(status);
    };
    ipcRenderer.on(IPC_CHANNELS.BACKEND_STATUS, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.BACKEND_STATUS, handler);
    };
  },

  // Assistant & Chat
  sendChatMessage: (message: string, context?: Record<string, unknown>): Promise<string> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SEND_CHAT_MESSAGE, { message, context });
  },
  onChatStream: (callback: (chunk: string) => void) => {
    const handler = (_event: unknown, chunk: string) => {
      callback(chunk);
    };
    ipcRenderer.on(IPC_CHANNELS.CHAT_STREAM_CHUNK, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.CHAT_STREAM_CHUNK, handler);
    };
  }
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
