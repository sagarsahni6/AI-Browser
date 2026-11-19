import type { BrowserTab, PageObservation } from '@ai-browser/shared';

export interface ElectronAPI {
  // Tabs
  createTab: (url?: string) => Promise<string>;
  closeTab: (tabId: string) => Promise<void>;
  switchTab: (tabId: string) => Promise<void>;
  getTabs: () => Promise<BrowserTab[]>;
  onTabsUpdated: (callback: (tabs: BrowserTab[], activeTabId: string) => void) => () => void;

  // Navigation
  navigate: (url: string) => Promise<void>;
  goBack: () => Promise<void>;
  goForward: () => Promise<void>;
  reload: () => Promise<void>;
  stop: () => Promise<void>;

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
  capturePage: () => Promise<string>; // base64 data url
  inspectPage: () => Promise<PageObservation>;

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
