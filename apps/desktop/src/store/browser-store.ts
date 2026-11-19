import { create } from 'zustand';
import type { BrowserTab, PageObservation } from '@ai-browser/shared';

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
  backendStatus: { online: boolean; port?: number };
  activeTab: BrowserTab | null;
  chatMessages: ChatMessage[];
  lastObservation: PageObservation | null;
  lastScreenshotUrl: string | null;

  // Actions
  setTabs: (tabs: BrowserTab[], activeTabId: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setAssistantOpen: (open: boolean) => void;
  setBackendStatus: (status: { online: boolean; port?: number }) => void;
  addChatMessage: (msg: ChatMessage) => void;
  appendChatChunk: (chunk: string) => void;
  setLastObservation: (obs: PageObservation | null) => void;
  setLastScreenshotUrl: (url: string | null) => void;

  // Browser Operations
  createTab: (url?: string) => Promise<void>;
  closeTab: (id: string) => Promise<void>;
  switchTab: (id: string) => Promise<void>;
  navigate: (url: string) => Promise<void>;
  goBack: () => Promise<void>;
  goForward: () => Promise<void>;
  reload: () => Promise<void>;
  toggleSidebar: () => Promise<void>;
  toggleAssistant: () => Promise<void>;
  capturePage: () => Promise<string>;
  inspectPage: () => Promise<PageObservation>;
  sendChatMessage: (content: string) => Promise<void>;
}

export const useBrowserStore = create<BrowserStore>((set, get) => ({
  tabs: [],
  activeTabId: '',
  sidebarOpen: false,
  assistantOpen: true,
  backendStatus: { online: false },
  activeTab: null,
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

  setTabs: (tabs, activeTabId) => {
    const activeTab = tabs.find(t => t.id === activeTabId) || null;
    set({ tabs, activeTabId, activeTab });
  },

  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setAssistantOpen: (assistantOpen) => set({ assistantOpen }),
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

  createTab: async (url) => {
    if (window.electronAPI?.createTab) {
      await window.electronAPI.createTab(url);
    }
  },

  closeTab: async (id) => {
    if (window.electronAPI?.closeTab) {
      await window.electronAPI.closeTab(id);
    }
  },

  switchTab: async (id) => {
    if (window.electronAPI?.switchTab) {
      await window.electronAPI.switchTab(id);
    }
  },

  navigate: async (url) => {
    if (window.electronAPI?.navigate) {
      await window.electronAPI.navigate(url);
    }
  },

  goBack: async () => {
    if (window.electronAPI?.goBack) {
      await window.electronAPI.goBack();
    }
  },

  goForward: async () => {
    if (window.electronAPI?.goForward) {
      await window.electronAPI.goForward();
    }
  },

  reload: async () => {
    if (window.electronAPI?.reload) {
      await window.electronAPI.reload();
    }
  },

  toggleSidebar: async () => {
    if (window.electronAPI?.toggleSidebar) {
      const open = await window.electronAPI.toggleSidebar();
      set({ sidebarOpen: open });
    }
  },

  toggleAssistant: async () => {
    if (window.electronAPI?.toggleAssistant) {
      const open = await window.electronAPI.toggleAssistant();
      set({ assistantOpen: open });
    }
  },

  capturePage: async () => {
    if (window.electronAPI?.capturePage) {
      const dataUrl = await window.electronAPI.capturePage();
      set({ lastScreenshotUrl: dataUrl });
      return dataUrl;
    }
    return '';
  },

  inspectPage: async () => {
    if (window.electronAPI?.inspectPage) {
      const obs = await window.electronAPI.inspectPage();
      set({ lastObservation: obs });
      return obs;
    }
    throw new Error('electronAPI not available');
  },

  sendChatMessage: async (content: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content,
      timestamp: Date.now()
    };
    get().addChatMessage(userMsg);

    if (window.electronAPI?.sendChatMessage) {
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        content: '',
        timestamp: Date.now()
      };
      get().addChatMessage(botMsg);
      const reply = await window.electronAPI.sendChatMessage(content, {
        tabId: get().activeTabId,
        url: get().activeTab?.url
      });
      // If full reply returned and not already streamed
      set(state => {
        const msgs = [...state.chatMessages];
        const last = msgs[msgs.length - 1];
        if (last && last.id === botMsg.id && !last.content) {
          msgs[msgs.length - 1] = { ...last, content: reply };
        }
        return { chatMessages: msgs };
      });
    }
  }
}));
