export interface BrowserTab {
  id: string;
  url: string;
  title: string;
  favicon?: string;
  isLoading: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
  isAudible?: boolean;
  isMuted?: boolean;
  isPrivate?: boolean;
  isPinned?: boolean;
}

export interface InteractiveElement {
  id: string;
  selector: string;
  tagName: string;
  role?: string;
  label?: string;
  text?: string;
  disabled?: boolean;
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface PageObservation {
  tabId: string;
  url: string;
  title: string;
  metaDescription?: string;
  viewport: {
    width: number;
    height: number;
  };
  visibleText: string;
  interactiveElements: InteractiveElement[];
}

export interface LayoutBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface HistoryItem {
  id: string;
  url: string;
  title: string;
  visitedAt: number;
  visitCount: number;
}

export interface BookmarkItem {
  id: string;
  url: string;
  title: string;
  favicon?: string;
  createdAt: number;
}

export interface DownloadItem {
  id: string;
  filename: string;
  url: string;
  savePath: string;
  receivedBytes: number;
  totalBytes: number;
  state: 'progressing' | 'completed' | 'cancelled' | 'interrupted';
  startTime: number;
}

export interface BrowserSession {
  tabs: Array<{ url: string; title: string }>;
  activeTabIndex: number;
  savedAt: number;
}
