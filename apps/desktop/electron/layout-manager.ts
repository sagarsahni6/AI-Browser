import type { BaseWindow, WebContentsView } from 'electron';

export interface LayoutState {
  toolbarHeight: number;
  sidebarWidth: number;
  assistantWidth: number;
  sidebarOpen: boolean;
  assistantOpen: boolean;
}

export class LayoutManager {
  private baseWindow: BaseWindow;
  private toolbarView: WebContentsView | null = null;
  private sidebarView: WebContentsView | null = null;
  private assistantView: WebContentsView | null = null;
  private activeTabView: WebContentsView | null = null;

  private state: LayoutState = {
    toolbarHeight: 76,
    sidebarWidth: 260,
    assistantWidth: 380,
    sidebarOpen: true,
    assistantOpen: true,
  };

  constructor(baseWindow: BaseWindow) {
    this.baseWindow = baseWindow;
  }

  public setViews(views: {
    toolbar?: WebContentsView;
    sidebar?: WebContentsView;
    assistant?: WebContentsView;
    activeTab?: WebContentsView;
  }) {
    if (views.toolbar !== undefined) this.toolbarView = views.toolbar;
    if (views.sidebar !== undefined) this.sidebarView = views.sidebar;
    if (views.assistant !== undefined) this.assistantView = views.assistant;
    if (views.activeTab !== undefined) this.activeTabView = views.activeTab;
    this.updateBounds();
  }

  public setActiveTabView(tabView: WebContentsView | null) {
    this.activeTabView = tabView;
    this.updateBounds();
  }

  public toggleSidebar(): boolean {
    this.state.sidebarOpen = !this.state.sidebarOpen;
    this.updateBounds();
    return this.state.sidebarOpen;
  }

  public setSidebarOpen(open: boolean): boolean {
    this.state.sidebarOpen = open;
    this.updateBounds();
    return this.state.sidebarOpen;
  }

  public toggleAssistant(): boolean {
    this.state.assistantOpen = !this.state.assistantOpen;
    this.updateBounds();
    return this.state.assistantOpen;
  }

  public setAssistantOpen(open: boolean): boolean {
    this.state.assistantOpen = open;
    this.updateBounds();
    return this.state.assistantOpen;
  }

  public isSidebarOpen(): boolean {
    return this.state.sidebarOpen;
  }

  public isAssistantOpen(): boolean {
    return this.state.assistantOpen;
  }

  public updateBounds() {
    if (this.baseWindow.isDestroyed()) return;

    // Get content bounds of the window
    const [winWidth, winHeight] = this.baseWindow.getContentSize();
    const { toolbarHeight, sidebarWidth, assistantWidth, sidebarOpen, assistantOpen } = this.state;

    const actualSidebarWidth = sidebarOpen ? sidebarWidth : 0;
    const actualAssistantWidth = assistantOpen ? assistantWidth : 0;
    const viewportY = toolbarHeight;
    const viewportHeight = Math.max(0, winHeight - toolbarHeight);
    const viewportWidth = Math.max(0, winWidth - actualSidebarWidth - actualAssistantWidth);

    // 1. Toolbar: full width across the top
    if (this.toolbarView && !this.toolbarView.webContents.isDestroyed()) {
      this.toolbarView.setBounds({
        x: 0,
        y: 0,
        width: winWidth,
        height: toolbarHeight,
      });
    }

    // 2. Sidebar: left below toolbar
    if (this.sidebarView && !this.sidebarView.webContents.isDestroyed()) {
      if (sidebarOpen) {
        this.sidebarView.setBounds({
          x: 0,
          y: viewportY,
          width: actualSidebarWidth,
          height: viewportHeight,
        });
      } else {
        this.sidebarView.setBounds({ x: 0, y: 0, width: 0, height: 0 });
      }
    }

    // 3. Central WebContentsView: active tab viewport
    if (this.activeTabView && !this.activeTabView.webContents.isDestroyed()) {
      this.activeTabView.setBounds({
        x: actualSidebarWidth,
        y: viewportY,
        width: viewportWidth,
        height: viewportHeight,
      });
    }

    // 4. Assistant: right below toolbar
    if (this.assistantView && !this.assistantView.webContents.isDestroyed()) {
      if (assistantOpen) {
        this.assistantView.setBounds({
          x: winWidth - actualAssistantWidth,
          y: viewportY,
          width: actualAssistantWidth,
          height: viewportHeight,
        });
      } else {
        this.assistantView.setBounds({ x: 0, y: 0, width: 0, height: 0 });
      }
    }
  }
}
