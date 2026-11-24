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
  setTabPinned: (tabId: string, isPinned: boolean): Promise<void> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TAB_SET_PINNED, tabId, isPinned);
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
  setSidebarOpen: (open: boolean): Promise<boolean> => {
    return ipcRenderer.invoke('panel:set-sidebar-open', open);
  },
  toggleAssistant: (): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.PANEL_TOGGLE_ASSISTANT);
  },
  setAssistantOpen: (open: boolean): Promise<boolean> => {
    return ipcRenderer.invoke('panel:set-assistant-open', open);
  },
  onAssistantStateChanged: (callback: (open: boolean) => void) => {
    const handler = (_event: unknown, open: boolean) => callback(open);
    ipcRenderer.on('panel:assistant-state-changed', handler);
    return () => {
      ipcRenderer.removeListener('panel:assistant-state-changed', handler);
    };
  },
  onSidebarStateChanged: (callback: (open: boolean) => void) => {
    const handler = (_event: unknown, open: boolean) => callback(open);
    ipcRenderer.on('panel:sidebar-state-changed', handler);
    return () => {
      ipcRenderer.removeListener('panel:sidebar-state-changed', handler);
    };
  },
  onChatIncomingPrompt: (callback: (prompt: string) => void) => {
    const handler = (_event: unknown, prompt: string) => callback(prompt);
    ipcRenderer.on('chat:incoming-prompt', handler);
    return () => {
      ipcRenderer.removeListener('chat:incoming-prompt', handler);
    };
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
  },

  // Multi-Agent Task Operations
  createTask: (title: string, prompt: string, options?: { engine?: string; provider?: string; model?: string; mode?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_CREATE, { title, prompt, ...options });
  },
  listTasks: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASKS_LIST);
  },
  getTask: (taskId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_GET, taskId);
  },
  cancelTask: (taskId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_CANCEL, taskId);
  },
  pauseTask: (taskId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_PAUSE, taskId);
  },
  resumeTask: (taskId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_RESUME, taskId);
  },
  approveTask: (taskId: string, decision: boolean = true, approvalId?: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_APPROVE, taskId, decision, approvalId);
  },
  rejectTask: (taskId: string, reason?: string, approvalId?: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.TASK_REJECT, taskId, reason, approvalId);
  },
  onTaskStepUpdate: (callback: (data: any) => void) => {
    const handler = (_event: unknown, data: any) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.TASK_STEP_UPDATED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.TASK_STEP_UPDATED, handler);
    };
  },
  onTaskStepUpdated: (callback: (data: any) => void) => {
    const handler = (_event: unknown, data: any) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.TASK_STEP_UPDATED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.TASK_STEP_UPDATED, handler);
    };
  },

  // Research Collections
  listCollections: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.COLLECTIONS_LIST);
  },
  createCollection: (name: string, description?: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.COLLECTION_CREATE, { name, description });
  },
  deleteCollection: (id: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.COLLECTION_DELETE, id);
  },

  // Workflows
  listWorkflows: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOWS_LIST);
  },
  getWorkflow: (id: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_GET, id);
  },
  saveWorkflow: (data: any): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_SAVE, data);
  },
  deleteWorkflow: (id: string): Promise<boolean> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_DELETE, id);
  },
  executeWorkflow: (id: string, variables?: any): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_EXECUTE, id, variables);
  },
  exportWorkflow: (id: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_EXPORT, id);
  },
  importWorkflow: (data: any): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_IMPORT, data);
  },
  startWorkflowRecording: (): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_RECORD_START);
  },
  stopWorkflowRecording: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.WORKFLOW_RECORD_STOP);
  },
  onWorkflowStepUpdate: (callback: (data: any) => void) => {
    const handler = (_event: unknown, data: any) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.WORKFLOW_STEP_UPDATE, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.WORKFLOW_STEP_UPDATE, handler);
    };
  },

  // Research & Document Intelligence + Advanced Data Extraction
  synthesizeResearch: (params: { topic: string; sources?: string[]; depth?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.RESEARCH_SYNTHESIZE, params);
  },
  listResearchReports: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.RESEARCH_LIST_REPORTS);
  },
  getResearchReport: (reportId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.RESEARCH_GET_REPORT, reportId);
  },
  deleteResearchReport: (reportId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.RESEARCH_DELETE_REPORT, reportId);
  },
  readPdf: (params: { path_or_url: string; max_pages?: number }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DOCUMENTS_READ_PDF, params);
  },
  summarizePdf: (params: { path_or_url: string; query?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DOCUMENTS_SUMMARIZE_PDF, params);
  },
  extractTableData: (params: { selector?: string; pagination_next_selector?: string; max_pages?: number }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DATA_EXTRACT_TABLE, params);
  },
  exportData: (params: { data: any[]; format?: string; filename?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DATA_EXPORT, params);
  },

  // Long-Term Memory
  remember: (params: { key: string; value: string; category?: string; tags?: string[] }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MEMORY_REMEMBER, params);
  },
  recallMemory: (params: { query: string; category?: string }): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MEMORY_RECALL, params);
  },
  getAllMemories: (category?: string): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MEMORY_GET_ALL, category);
  },
  forgetMemory: (memoryId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MEMORY_FORGET, memoryId);
  },

  // Website Monitors
  createMonitor: (params: { url: string; name: string; selector?: string; check_interval?: number }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MONITORS_CREATE, params);
  },
  listMonitors: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MONITORS_LIST);
  },
  checkMonitorNow: (monitorId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MONITORS_CHECK_NOW, monitorId);
  },
  deleteMonitor: (monitorId: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.MONITORS_DELETE, monitorId);
  },
  onMonitorAlert: (callback: (data: any) => void) => {
    const handler = (_event: unknown, data: any) => {
      callback(data);
    };
    ipcRenderer.on(IPC_CHANNELS.MONITOR_CHANGE_DETECTED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.MONITOR_CHANGE_DETECTED, handler);
    };
  },

  // Windows Desktop Automation
  desktopClick: (params: { x: number; y: number; button?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_CLICK, params);
  },
  desktopType: (text: string): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_TYPE, text);
  },
  desktopHotkey: (keys: string[]): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_HOTKEY, keys);
  },
  desktopCaptureScreen: (): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_CAPTURE_SCREEN);
  },
  desktopLaunchApp: (params: { app_name: string; args?: string[] }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_LAUNCH_APP, params);
  },
  desktopEmergencyStop: (): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_EMERGENCY_STOP);
  },
  desktopResetStop: (): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_RESET_STOP);
  },
  desktopGetAuditLogs: (limit?: number): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.DESKTOP_GET_AUDIT_LOGS, limit);
  },
  onDesktopEmergencyStopped: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on(IPC_CHANNELS.DESKTOP_EMERGENCY_STOPPED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.DESKTOP_EMERGENCY_STOPPED, handler);
    };
  },

  // Command Palette
  onToggleCommandPalette: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on('command-palette:toggle', handler);
    return () => {
      ipcRenderer.removeListener('command-palette:toggle', handler);
    };
  },

  // Comet Visual Laser Indicator
  onLaserIndicator: (callback: (coords: { x: number; y: number }) => void) => {
    const handler = (_event: unknown, coords: { x: number; y: number }) => {
      callback(coords);
    };
    ipcRenderer.on(IPC_CHANNELS.COMET_LASER_INDICATOR, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.COMET_LASER_INDICATOR, handler);
    };
  },

  // Dedicated Approval IPC
  sendApprovalResponse: (payload: { taskId: string; approved: boolean; reason?: string }): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.APPROVAL_RESPONSE, payload);
  },

  // Agent Skills Architecture
  listSkills: (): Promise<any[]> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SKILLS_LIST);
  },
  toggleSkill: (skillId: string, enabled?: boolean): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SKILLS_TOGGLE, skillId, enabled);
  },
  executeSkill: (toolName: string, params?: any): Promise<any> => {
    return ipcRenderer.invoke(IPC_CHANNELS.SKILLS_EXECUTE, { toolName, params });
  },
  onSkillsChanged: (callback: (data: any) => void) => {
    const handler = (_event: unknown, data: any) => callback(data);
    ipcRenderer.on(IPC_CHANNELS.SKILLS_CHANGED, handler);
    return () => {
      ipcRenderer.removeListener(IPC_CHANNELS.SKILLS_CHANGED, handler);
    };
  }
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
