import type {
  BrowserTab,
  PageObservation,
  HistoryItem,
  BookmarkItem,
  DownloadItem
} from '@ai-browser/shared';

export interface ElectronAPI {
  // Tabs
  createTab: (url?: string, isPrivate?: boolean) => Promise<string>;
  closeTab: (tabId: string) => Promise<void>;
  switchTab: (tabId: string) => Promise<void>;
  getTabs: () => Promise<BrowserTab[]>;
  restoreClosedTab: () => Promise<string | null>;
  duplicateTab: (tabId: string) => Promise<void>;
  onTabsUpdated: (callback: (tabs: BrowserTab[], activeTabId: string) => void) => () => void;

  // Navigation
  navigate: (url: string) => Promise<void>;
  goBack: () => Promise<void>;
  goForward: () => Promise<void>;
  reload: () => Promise<void>;
  stop: () => Promise<void>;

  // History
  getHistory: (limit?: number) => Promise<HistoryItem[]>;
  searchHistory: (query: string) => Promise<HistoryItem[]>;
  clearHistory: () => Promise<void>;

  // Bookmarks
  getBookmarks: () => Promise<BookmarkItem[]>;
  addBookmark: (item: { url: string; title: string; favicon?: string }) => Promise<BookmarkItem>;
  removeBookmark: (urlOrId: string) => Promise<boolean>;
  isBookmarked: (url: string) => Promise<boolean>;

  // Downloads
  getDownloads: () => Promise<DownloadItem[]>;
  openDownloadFile: (id: string) => Promise<boolean>;
  openDownloadFolder: (id: string) => Promise<boolean>;
  onDownloadUpdate: (callback: (item: DownloadItem) => void) => () => void;

  // Panels
  toggleSidebar: () => Promise<boolean>;
  toggleAssistant: () => Promise<boolean>;
  getInitialState: () => Promise<{
    tabs: BrowserTab[];
    activeTabId: string;
    sidebarOpen: boolean;
    assistantOpen: boolean;
    backendStatus: { online: boolean; port?: number };
  }>;

  // Browser Actions & CDP
  capturePage: () => Promise<string>;
  inspectPage: () => Promise<PageObservation>;

  // Secrets & Settings
  setSecret: (key: string, value: string) => Promise<void>;
  getSecret: (key: string) => Promise<string | null>;

  // Backend state
  onBackendStatus: (callback: (status: { online: boolean; port?: number }) => void) => () => void;

  // Assistant & Chat
  sendChatMessage: (message: string, context?: Record<string, unknown>) => Promise<string>;
  onChatStream: (callback: (chunk: string) => void) => () => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
