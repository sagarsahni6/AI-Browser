import { describe, it, expect, beforeEach } from 'vitest';
import { useBrowserStore } from '../src/store/browser-store';

describe('Phase 1: Core Browser State & Features', () => {
  beforeEach(() => {
    useBrowserStore.setState({
      tabs: [],
      activeTabId: '',
      bookmarks: [],
      history: [],
      downloads: [],
      isCurrentPageBookmarked: false,
      sidebarActiveTab: 'discover'
    });
  });

  it('manages bookmark collection and status', () => {
    const bm1 = { id: 'bm-1', url: 'https://example.com', title: 'Example', createdAt: Date.now() };
    useBrowserStore.setState({ bookmarks: [bm1] });

    expect(useBrowserStore.getState().bookmarks.length).toBe(1);
    expect(useBrowserStore.getState().bookmarks[0].title).toBe('Example');

    // Setting tabs updates isCurrentPageBookmarked
    useBrowserStore.getState().setTabs([
      { id: 'tab-1', url: 'https://example.com', title: 'Example', isLoading: false, canGoBack: false, canGoForward: false }
    ], 'tab-1');

    expect(useBrowserStore.getState().isCurrentPageBookmarked).toBe(true);
  });

  it('switches sidebar tabs between history, bookmarks and downloads', () => {
    useBrowserStore.getState().setSidebarActiveTab('history');
    expect(useBrowserStore.getState().sidebarActiveTab).toBe('history');
    expect(useBrowserStore.getState().sidebarOpen).toBe(true);

    useBrowserStore.getState().setSidebarActiveTab('downloads');
    expect(useBrowserStore.getState().sidebarActiveTab).toBe('downloads');
  });

  it('tracks downloads progress and completion updates', () => {
    const dl1 = {
      id: 'dl-1',
      filename: 'report.pdf',
      url: 'https://example.com/report.pdf',
      savePath: 'C:\\Downloads\\report.pdf',
      receivedBytes: 1024,
      totalBytes: 2048,
      state: 'progressing' as const,
      startTime: Date.now()
    };

    useBrowserStore.getState().updateDownloadItem(dl1);
    expect(useBrowserStore.getState().downloads.length).toBe(1);
    expect(useBrowserStore.getState().downloads[0].state).toBe('progressing');

    // Update with completed
    useBrowserStore.getState().updateDownloadItem({
      ...dl1,
      receivedBytes: 2048,
      state: 'completed'
    });

    expect(useBrowserStore.getState().downloads[0].receivedBytes).toBe(2048);
    expect(useBrowserStore.getState().downloads[0].state).toBe('completed');
  });
});
