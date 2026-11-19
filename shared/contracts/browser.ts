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
}

export interface InteractiveElement {
  id: string;
  tagName: string;
  role?: string;
  label?: string;
  text?: string;
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
