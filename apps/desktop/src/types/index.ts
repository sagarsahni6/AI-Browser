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
  setTabPinned?: (tabId: string, isPinned: boolean) => Promise<void>;
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
  setSidebarOpen: (open: boolean) => Promise<boolean>;
  toggleAssistant: () => Promise<boolean>;
  setAssistantOpen: (open: boolean) => Promise<boolean>;
  onAssistantStateChanged?: (callback: (open: boolean) => void) => () => void;
  onSidebarStateChanged?: (callback: (open: boolean) => void) => () => void;
  onChatIncomingPrompt?: (callback: (prompt: string) => void) => () => void;
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
  stopAssistant: () => Promise<boolean>;
  onChatAction: (callback: (data: { action: string; parameters?: any; status: string; result?: any }) => void) => () => void;

  // Multi-Agent Task Operations
  createTask?: (title: string, prompt: string, options?: { engine?: string; provider?: string; model?: string; mode?: string }) => Promise<any>;
  listTasks?: () => Promise<any[]>;
  getTask?: (taskId: string) => Promise<any>;
  cancelTask?: (taskId: string) => Promise<any>;
  pauseTask?: (taskId: string) => Promise<any>;
  resumeTask?: (taskId: string) => Promise<any>;
  approveTask?: (taskId: string, decision?: boolean) => Promise<any>;
  rejectTask?: (taskId: string, reason?: string) => Promise<any>;
  onTaskStepUpdate?: (callback: (data: any) => void) => () => void;

  // Collections
  listCollections?: () => Promise<any[]>;
  createCollection?: (name: string, description?: string) => Promise<any>;
  deleteCollection?: (id: string) => Promise<boolean>;

  // Workflows
  listWorkflows?: () => Promise<any[]>;
  getWorkflow?: (id: string) => Promise<any>;
  saveWorkflow?: (data: any) => Promise<any>;
  deleteWorkflow?: (id: string) => Promise<boolean>;
  executeWorkflow?: (id: string, variables?: any) => Promise<any>;
  exportWorkflow?: (id: string) => Promise<any>;
  importWorkflow?: (data: any) => Promise<any>;
  startWorkflowRecording?: () => Promise<any>;
  stopWorkflowRecording?: () => Promise<any[]>;
  onWorkflowStepUpdate?: (callback: (data: any) => void) => () => void;

  // Research & Document Intelligence + Advanced Data Extraction
  synthesizeResearch?: (params: { topic: string; sources?: string[]; depth?: string }) => Promise<any>;
  listResearchReports?: () => Promise<any[]>;
  getResearchReport?: (reportId: string) => Promise<any>;
  deleteResearchReport?: (reportId: string) => Promise<any>;
  readPdf?: (params: { path_or_url: string; max_pages?: number }) => Promise<any>;
  summarizePdf?: (params: { path_or_url: string; query?: string }) => Promise<any>;
  extractTableData?: (params: { selector?: string; pagination_next_selector?: string; max_pages?: number }) => Promise<any>;
  exportData?: (params: { data: any[]; format?: string; filename?: string }) => Promise<any>;

  // Long-Term Memory
  remember?: (params: { key: string; value: string; category?: string; tags?: string[] }) => Promise<any>;
  recallMemory?: (params: { query: string; category?: string }) => Promise<any[]>;
  getAllMemories?: (category?: string) => Promise<any[]>;
  forgetMemory?: (memoryId: string) => Promise<any>;

  // Website Monitors
  createMonitor?: (params: { url: string; name: string; selector?: string; check_interval?: number }) => Promise<any>;
  listMonitors?: () => Promise<any[]>;
  checkMonitorNow?: (monitorId: string) => Promise<any>;
  deleteMonitor?: (monitorId: string) => Promise<any>;
  onMonitorAlert?: (callback: (data: any) => void) => () => void;

  // Windows Desktop Automation
  desktopClick?: (params: { x: number; y: number; button?: string }) => Promise<any>;
  desktopType?: (text: string) => Promise<any>;
  desktopHotkey?: (keys: string[]) => Promise<any>;
  desktopCaptureScreen?: () => Promise<any>;
  desktopLaunchApp?: (params: { app_name: string; args?: string[] }) => Promise<any>;
  desktopEmergencyStop?: () => Promise<any>;
  desktopResetStop?: () => Promise<any>;
  desktopGetAuditLogs?: (limit?: number) => Promise<any[]>;
  onDesktopEmergencyStopped?: (callback: () => void) => () => void;

  // Command Palette & Laser Indicator
  onToggleCommandPalette?: (callback: () => void) => () => void;
  onLaserIndicator?: (callback: (coords: { x: number; y: number }) => void) => () => void;
  sendApprovalResponse?: (payload: { taskId: string; approved: boolean; reason?: string }) => Promise<any>;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
