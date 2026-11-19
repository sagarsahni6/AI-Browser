import { describe, it, expect, beforeEach } from 'vitest';
import { useBrowserStore } from '../src/store/browser-store';

describe('useBrowserStore', () => {
  beforeEach(() => {
    useBrowserStore.setState({
      tabs: [],
      activeTabId: '',
      sidebarOpen: false,
      assistantOpen: true,
      backendStatus: { online: false },
    });
  });

  it('updates tabs and activeTab correctly', () => {
    const tabs = [
      { id: 'tab-1', url: 'https://example.com', title: 'Example', isLoading: false, canGoBack: false, canGoForward: false },
      { id: 'tab-2', url: 'https://google.com', title: 'Google', isLoading: false, canGoBack: true, canGoForward: false }
    ];

    useBrowserStore.getState().setTabs(tabs, 'tab-2');

    const state = useBrowserStore.getState();
    expect(state.tabs.length).toBe(2);
    expect(state.activeTabId).toBe('tab-2');
    expect(state.activeTab?.title).toBe('Google');
  });

  it('toggles sidebar and assistant panels', () => {
    expect(useBrowserStore.getState().sidebarOpen).toBe(false);
    useBrowserStore.getState().setSidebarOpen(true);
    expect(useBrowserStore.getState().sidebarOpen).toBe(true);

    expect(useBrowserStore.getState().assistantOpen).toBe(true);
    useBrowserStore.getState().setAssistantOpen(false);
    expect(useBrowserStore.getState().assistantOpen).toBe(false);
  });
});
