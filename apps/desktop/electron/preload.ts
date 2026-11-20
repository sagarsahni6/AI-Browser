import { contextBridge, ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '@ai-browser/shared';
import type { BrowserTab, PageObservation, HistoryItem, BookmarkItem, DownloadItem } from '@ai-browser/shared';

const electronAPI = {
  // Tabs
  createTab: (url?: string, isPrivate?: boolean): Promise<string> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_CREATE, url, isPrivate);
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
  restoreClosedTab: (): Promise<string | null> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_RESTORE_CLOSED);
  },
  duplicateTab: (tabId: string): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_DUPLICATE, tabId);
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

  // History
  getHistory: (limit?: number): Promise<HistoryItem[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.HISTORY_GET, limit);
  },
  searchHistory: (query: string): Promise<HistoryItem[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.HISTORY_SEARCH, query);
  },
  clearHistory: (): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.HISTORY_CLEAR);
  },

  // Bookmarks
  getBookmarks: (): Promise<BookmarkItem[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.BOOKMARKS_GET);
  },
  addBookmark: (item: { url: string; title: string; favicon?: string }): Promise<BookmarkItem> => {
    return ipcRenderer.invoke(IPC_CHANNELS.BOOKMARK_ADD, item);
  },
  removeBookmark: (urlOrId: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.BOOKMARK_REMOVE, urlOrId);
  },
  isBookmarked: (url: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.BOOKMARK_IS_SAVED, url);
  },

  // Downloads
  getDownloads: (): Promise<DownloadItem[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DOWNLOADS_GET);
  },
  openDownloadFile: (id: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DOWNLOAD_OPEN_FILE, id);
  },
  openDownloadFolder: (id: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DOWNLOAD_OPEN_FOLDER, id);
  },
  onDownloadUpdate: (callback: (item: DownloadItem) => void) => {
    const handler = (_event: unknown, item: DownloadItem) => {
      callback(item);
    };
    ipcRenderer.on(IPC_CHANNELS.DOWNLOAD_UPDATE, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.DOWNLOAD_UPDATE, handler);
    };
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

  // Secrets & Settings
  setSecret: (key: string, value: string): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SECRET_SET, key, value);
  },
  getSecret: (key: string): Promise<string | null> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SECRET_GET, key);
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
  },
  stopAssistant: (): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.STOP_ASSISTANT);
  },
  onChatAction: (callback: (data: { action: string; parameters?: any; status: string; result?: any }) => void) => {
    const handler = (_event: unknown, data: any) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.CHAT_ACTION_UPDATE, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.CHAT_ACTION_UPDATE, handler);
    };
  }
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
