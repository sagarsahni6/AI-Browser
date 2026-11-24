import { create } from 'zustand';
import type { BrowserTab, PageObservation, BookmarkItem, HistoryItem, DownloadItem, SkillManifest } from '@ai-browser/shared';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

interface BrowserStore {
  tabs: BrowserTab[];
  activeTabId: string;
  sidebarOpen: boolean;
  assistantOpen: boolean;
  sidebarActiveTab: 'discover' | 'history' | 'bookmarks' | 'downloads' | 'collections' | 'workflows' | 'research' | 'tasks' | 'skills' | 'settings';
  backendStatus: { online: boolean; port?: number };
  activeTab: BrowserTab | null;
  chatMessages: ChatMessage[];
  lastObservation: PageObservation | null;
  lastScreenshotUrl: string | null;
  bookmarks: BookmarkItem[];
  history: HistoryItem[];
  downloads: DownloadItem[];
  isCurrentPageBookmarked: boolean;
  theme: 'light' | 'dark';

  // Actions
  setTabs: (tabs: BrowserTab[], activeTabId: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setSidebarActiveTab: (tab: 'discover' | 'history' | 'bookmarks' | 'downloads' | 'collections' | 'workflows' | 'research' | 'tasks' | 'skills' | 'settings') => void;
  setAssistantOpen: (open: boolean) => void;
  setBackendStatus: (status: { online: boolean; port?: number }) => void;
  addChatMessage: (msg: ChatMessage) => void;
  appendChatChunk: (chunk: string) => void;
  setLastObservation: (obs: PageObservation | null) => void;
  setLastScreenshotUrl: (url: string | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // Browser Operations
  createTab: (url?: string, isPrivate?: boolean) => Promise<void>;
  closeTab: (id: string) => Promise<void>;
  switchTab: (id: string) => Promise<void>;
  restoreClosedTab: () => Promise<void>;
  duplicateTab: (id: string) => Promise<void>;
  setTabPinned: (id: string, isPinned: boolean) => Promise<void>;
  navigate: (url: string) => Promise<void>;
  goBack: () => Promise<void>;
  goForward: () => Promise<void>;
  reload: () => Promise<void>;
  toggleSidebar: () => Promise<void>;
  toggleAssistant: () => Promise<void>;
  capturePage: () => Promise<string>;
  inspectPage: () => Promise<PageObservation>;
  sendChatMessage: (content: string, context?: Record<string, unknown>) => Promise<void>;
  stopAssistant: () => Promise<void>;
  isAgentRunning: boolean;
  activeAction: {
    action: string;
    parameters?: any;
    status: string;
    result?: any;
    step_number?: number;
    total_steps?: number;
    thought?: string;
    plan?: any;
  } | null;
  setActiveAction: (action: {
    action: string;
    parameters?: any;
    status: string;
    result?: any;
    step_number?: number;
    total_steps?: number;
    thought?: string;
    plan?: any;
  } | null) => void;

  // History & Bookmarks & Downloads
  refreshBookmarks: () => Promise<void>;
  toggleBookmarkCurrentPage: () => Promise<void>;
  removeBookmark: (urlOrId: string) => Promise<void>;
  refreshHistory: () => Promise<void>;
  searchHistory: (query: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  refreshDownloads: () => Promise<void>;
  openDownloadFile: (id: string) => Promise<void>;
  openDownloadFolder: (id: string) => Promise<void>;
  updateDownloadItem: (item: DownloadItem) => void;

  // Agent Skills
  skills: SkillManifest[];
  loadSkills: () => Promise<void>;
  toggleSkill: (id: string, enabled?: boolean) => Promise<void>;
  executeSkill: (toolName: string, params?: any) => Promise<any>;
}

export function applyTheme(theme: 'light' | 'dark') {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    if (document.body) {
      document.body.setAttribute('data-theme', theme);
      document.body.classList.remove('light', 'dark');
      document.body.classList.add(theme);
    }
  }
}

function getInitialTheme(): 'light' | 'dark' {
  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = window.localStorage.getItem('app_theme');
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
  }
  return 'light';
}

const initialTheme = getInitialTheme();
applyTheme(initialTheme);

const themeChannel = typeof window !== 'undefined' && 'BroadcastChannel' in window
  ? new BroadcastChannel('ai_browser_theme_sync')
  : null;

const getApi = () => (typeof window !== 'undefined' ? window.electronAPI : undefined);

export const useBrowserStore = create<BrowserStore>((set, get) => ({
  tabs: [],
  activeTabId: '',
  sidebarOpen: true,
  assistantOpen: true,
  sidebarActiveTab: 'discover',
  backendStatus: { online: false },
  activeTab: null,
  theme: initialTheme,
  chatMessages: [
    {
      id: 'welcome-1',
      sender: 'assistant',
      content: 'Welcome to AI Browser. I can inspect pages via CDP, capture screenshots, summarize content, and conduct research.',
      timestamp: Date.now()
    }
  ],
  lastObservation: null,
  lastScreenshotUrl: null,
  bookmarks: [],
  history: [],
  downloads: [],
  isCurrentPageBookmarked: false,
  isAgentRunning: false,
  activeAction: null,
  setActiveAction: (action) => set({ activeAction: action }),
  stopAssistant: async () => {
    if (window.electronAPI?.stopAssistant) {
      await window.electronAPI.stopAssistant();
    }
    set({ isAgentRunning: false, activeAction: null });
  },

  setTheme: (theme: 'light' | 'dark') => {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem('app_theme', theme);
    }
    applyTheme(theme);
    themeChannel?.postMessage({ type: 'THEME_CHANGE', theme });
    set({ theme });
  },

  toggleTheme: () => {
    const nextTheme = get().theme === 'light' ? 'dark' : 'light';
    get().setTheme(nextTheme);
  },

  setTabs: (tabs, activeTabId) => {
    const activeTab = tabs.find(t => t.id === activeTabId) || null;
    const isBookmarked = activeTab ? get().bookmarks.some(b => b.url === activeTab.url) : false;
    set({ tabs, activeTabId, activeTab, isCurrentPageBookmarked: isBookmarked });
  },

  setSidebarOpen: (sidebarOpen) => {
    const api = getApi();
    if (api?.setSidebarOpen) {
      api.setSidebarOpen(sidebarOpen);
    }
    set({ sidebarOpen });
  },
  setSidebarActiveTab: (sidebarActiveTab) => {
    const api = getApi();
    if (api?.setSidebarOpen) {
      api.setSidebarOpen(true);
    }
    set({ sidebarActiveTab, sidebarOpen: true });
  },
  setAssistantOpen: (assistantOpen) => {
    const api = getApi();
    if (api?.setAssistantOpen) {
      api.setAssistantOpen(assistantOpen);
    }
    set({ assistantOpen });
  },
  setBackendStatus: (backendStatus) => set({ backendStatus }),

  addChatMessage: (msg) => {
    set(state => ({ chatMessages: [...state.chatMessages, msg] }));
  },

  appendChatChunk: (chunk) => {
    set(state => {
      const msgs = [...state.chatMessages];
      const last = msgs[msgs.length - 1];
      if (last && last.sender === 'assistant') {
        msgs[msgs.length - 1] = {
          ...last,
          content: last.content + chunk
        };
      }
      return { chatMessages: msgs };
    });
  },

  setLastObservation: (obs) => set({ lastObservation: obs }),
  setLastScreenshotUrl: (url) => set({ lastScreenshotUrl: url }),

  createTab: async (url, isPrivate) => {
    const api = getApi();
    if (api?.createTab) {
      await api.createTab(url, isPrivate);
    }
  },

  closeTab: async (id) => {
    const api = getApi();
    if (api?.closeTab) {
      await api.closeTab(id);
    }
  },

  switchTab: async (id) => {
    const api = getApi();
    if (api?.switchTab) {
      await api.switchTab(id);
    }
  },

  restoreClosedTab: async () => {
    const api = getApi();
    if (api?.restoreClosedTab) {
      await api.restoreClosedTab();
    }
  },

  duplicateTab: async (id) => {
    const api = getApi();
    if (api?.duplicateTab) {
      await api.duplicateTab(id);
    }
  },

  setTabPinned: async (id: string, isPinned: boolean) => {
    const api = getApi();
    if (api?.setTabPinned) {
      await api.setTabPinned(id, isPinned);
    }
  },

  navigate: async (url) => {
    const api = getApi();
    if (api?.navigate) {
      await api.navigate(url);
    }
  },

  goBack: async () => {
    const api = getApi();
    if (api?.goBack) {
      await api.goBack();
    }
  },

  goForward: async () => {
    const api = getApi();
    if (api?.goForward) {
      await api.goForward();
    }
  },

  reload: async () => {
    const api = getApi();
    if (api?.reload) {
      await api.reload();
    }
  },

  toggleSidebar: async () => {
    const api = getApi();
    if (api?.toggleSidebar) {
      const open = await api.toggleSidebar();
      set({ sidebarOpen: open });
    }
  },

  toggleAssistant: async () => {
    const api = getApi();
    if (api?.toggleAssistant) {
      const open = await api.toggleAssistant();
      set({ assistantOpen: open });
    }
  },

  capturePage: async () => {
    const api = getApi();
    if (api?.capturePage) {
      const dataUrl = await api.capturePage();
      set({ lastScreenshotUrl: dataUrl });
      return dataUrl;
    }
    return '';
  },

  inspectPage: async () => {
    const api = getApi();
    if (api?.inspectPage) {
      const obs = await api.inspectPage();
      set({ lastObservation: obs });
      return obs;
    }
    throw new Error('electronAPI not available');
  },

  sendChatMessage: async (content: string, context?: Record<string, unknown>) => {
    get().setAssistantOpen(true);
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content,
      timestamp: Date.now()
    };
    get().addChatMessage(userMsg);

    const api = getApi();
    if (api?.sendChatMessage) {
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        content: '',
        timestamp: Date.now()
      };
      get().addChatMessage(botMsg);
      set({ isAgentRunning: true });

      try {
        const reply = await api.sendChatMessage(content, {
          tabId: get().activeTabId,
          url: get().activeTab?.url,
          ...(context || {})
        });
        set(state => {
          const msgs = [...state.chatMessages];
          const last = msgs[msgs.length - 1];
          if (last && last.id === botMsg.id) {
            msgs[msgs.length - 1] = { ...last, content: reply || last.content };
          }
          return { chatMessages: msgs };
        });
      } finally {
        set({ isAgentRunning: false, activeAction: null });
      }
    }
  },

  refreshBookmarks: async () => {
    if (window.electronAPI?.getBookmarks) {
      const list = await window.electronAPI.getBookmarks();
      const isBookmarked = get().activeTab ? list.some(b => b.url === get().activeTab?.url) : false;
      set({ bookmarks: list, isCurrentPageBookmarked: isBookmarked });
    }
  },

  toggleBookmarkCurrentPage: async () => {
    const active = get().activeTab;
    if (!active || !window.electronAPI?.addBookmark || !window.electronAPI?.removeBookmark) return;

    if (get().isCurrentPageBookmarked) {
      await window.electronAPI.removeBookmark(active.url);
      set({
        isCurrentPageBookmarked: false,
        bookmarks: get().bookmarks.filter(b => b.url !== active.url)
      });
    } else {
      const newItem = await window.electronAPI.addBookmark({
        url: active.url,
        title: active.title || active.url,
        favicon: active.favicon
      });
      set({
        isCurrentPageBookmarked: true,
        bookmarks: [newItem, ...get().bookmarks]
      });
    }
  },

  removeBookmark: async (urlOrId) => {
    if (window.electronAPI?.removeBookmark) {
      await window.electronAPI.removeBookmark(urlOrId);
      set(state => ({
        bookmarks: state.bookmarks.filter(b => b.id !== urlOrId && b.url !== urlOrId),
        isCurrentPageBookmarked: state.activeTab ? state.activeTab.url !== urlOrId : false
      }));
    }
  },

  refreshHistory: async () => {
    if (window.electronAPI?.getHistory) {
      const list = await window.electronAPI.getHistory(150);
      set({ history: list });
    }
  },

  searchHistory: async (query) => {
    if (window.electronAPI?.searchHistory) {
      const results = await window.electronAPI.searchHistory(query);
      set({ history: results });
    }
  },

  clearHistory: async () => {
    if (window.electronAPI?.clearHistory) {
      await window.electronAPI.clearHistory();
      set({ history: [] });
    }
  },

  refreshDownloads: async () => {
    if (window.electronAPI?.getDownloads) {
      const list = await window.electronAPI.getDownloads();
      set({ downloads: list });
    }
  },

  openDownloadFile: async (id) => {
    if (window.electronAPI?.openDownloadFile) {
      await window.electronAPI.openDownloadFile(id);
    }
  },

  openDownloadFolder: async (id) => {
    if (window.electronAPI?.openDownloadFolder) {
      await window.electronAPI.openDownloadFolder(id);
    }
  },

  updateDownloadItem: (item) => {
    set(state => {
      const idx = state.downloads.findIndex(d => d.id === item.id);
      if (idx !== -1) {
        const next = [...state.downloads];
        next[idx] = item;
        return { downloads: next };
      }
      return { downloads: [item, ...state.downloads] };
    });
  },

  skills: [],
  loadSkills: async () => {
    if (window.electronAPI?.listSkills) {
      try {
        const list = await window.electronAPI.listSkills();
        set({ skills: list || [] });
      } catch (e) {
        console.error('Failed to load skills:', e);
      }
    }
  },
  toggleSkill: async (id: string, enabled?: boolean) => {
    if (window.electronAPI?.toggleSkill) {
      try {
        const res = await window.electronAPI.toggleSkill(id, enabled);
        set(state => ({
          skills: state.skills.map(s => s.id === id ? { ...s, enabled: res.enabled } : s)
        }));
      } catch (e) {
        console.error('Failed to toggle skill:', e);
      }
    }
  },
  executeSkill: async (toolName: string, params?: any) => {
    if (window.electronAPI?.executeSkill) {
      return await window.electronAPI.executeSkill(toolName, params);
    }
    throw new Error('electronAPI.executeSkill not available');
  }
}));

if (typeof window !== 'undefined') {
  if (themeChannel) {
    themeChannel.onmessage = (event) => {
      if (event.data?.type === 'THEME_CHANGE' && (event.data.theme === 'light' || event.data.theme === 'dark')) {
        applyTheme(event.data.theme);
        useBrowserStore.setState({ theme: event.data.theme });
      }
    };
  }

  window.addEventListener('storage', (event) => {
    if (event.key === 'app_theme' && (event.newValue === 'light' || event.newValue === 'dark')) {
      const newTheme = event.newValue as 'light' | 'dark';
      applyTheme(newTheme);
      useBrowserStore.setState({ theme: newTheme });
    }
  });
}
