import { app, BaseWindow, Menu } from 'electron';
import { createPanelView } from './panels/panel-factory';
import { LayoutManager } from './layout-manager';
import { TabManager } from './browser/tab-manager';
import { DebuggerManager } from './browser/debugger-manager';
import { HistoryManager } from './browser/history-manager';
import { BookmarkManager } from './browser/bookmark-manager';
import { DownloadManager } from './browser/download-manager';
import { SessionManager } from './browser/session-manager';
import { RpcClient } from './bridge/rpc-client';
import { ProcessManager } from './bridge/process-manager';
import { setupIpcHandlers } from './bridge/ipc-handlers';

let mainWindow: BaseWindow | null = null;
let tabManager: TabManager | null = null;
let debuggerManager: DebuggerManager | null = null;
let historyManager: HistoryManager | null = null;
let bookmarkManager: BookmarkManager | null = null;
let downloadManager: DownloadManager | null = null;
let sessionManager: SessionManager | null = null;
let processManager: ProcessManager | null = null;

async function createWindow() {
  Menu.setApplicationMenu(null);
  mainWindow = new BaseWindow({
    width: 1360,
    height: 860,
    minWidth: 840,
    minHeight: 600,
    show: false,
    title: 'AI Browser',
    backgroundColor: '#f8fafc',
  });

  const layoutManager = new LayoutManager(mainWindow);
  debuggerManager = new DebuggerManager();
  historyManager = new HistoryManager();
  bookmarkManager = new BookmarkManager();
  downloadManager = new DownloadManager();
  sessionManager = new SessionManager();

  tabManager = new TabManager(mainWindow, debuggerManager, historyManager, sessionManager);
  const rpcClient = new RpcClient();
  processManager = new ProcessManager(rpcClient);

  // 1. Create panel views
  const toolbarView = createPanelView('toolbar');
  const sidebarView = createPanelView('sidebar');
  const assistantView = createPanelView('assistant');

  mainWindow.contentView.addChildView(toolbarView);
  mainWindow.contentView.addChildView(sidebarView);
  mainWindow.contentView.addChildView(assistantView);

  layoutManager.setViews({
    toolbar: toolbarView,
    sidebar: sidebarView,
    assistant: assistantView,
  });

  tabManager.setCallbacks({
    onActiveTabChanged: (tabView) => {
      layoutManager.setActiveTabView(tabView);
    },
    onToggleSidebar: () => {
      layoutManager.toggleSidebar();
    },
    onToggleAssistant: () => {
      layoutManager.toggleAssistant();
    },
    onBookmarkPage: (url, title) => {
      bookmarkManager?.addBookmark({ url, title });
    },
    onAskAI: (text) => {
      if (!assistantView.webContents.isDestroyed()) {
        assistantView.webContents.send('chat:incoming-prompt', text);
      }
    },
    onOpenCommandPalette: () => {
      if (!toolbarView.webContents.isDestroyed()) {
        toolbarView.webContents.send('command-palette:toggle');
      }
    }
  });

  // Setup IPC Handlers
  setupIpcHandlers({
    tabManager,
    layoutManager,
    processManager,
    rpcClient,
    historyManager,
    bookmarkManager,
    downloadManager,
    panelViews: [toolbarView, sidebarView, assistantView],
  });

  // Resize listeners
  mainWindow.on('resize', () => layoutManager.updateBounds());
  mainWindow.on('maximize', () => layoutManager.updateBounds());
  mainWindow.on('unmaximize', () => layoutManager.updateBounds());

  // Restore previous session or start clean
  const savedSession = sessionManager.loadSession();
  if (savedSession && savedSession.tabs && savedSession.tabs.length > 0) {
    for (const t of savedSession.tabs) {
      await tabManager.createTab(t.url);
    }
  } else {
    await tabManager.createTab('https://example.com');
  }

  mainWindow.show();
  layoutManager.updateBounds();

  // Start Python backend process
  processManager.start().catch((err) => {
    console.error('[Main] Failed to start Python process:', err);
  });

  // Cleanup on window close
  mainWindow.on('closed', () => {
    if (tabManager) tabManager.dispose();
    if (debuggerManager) debuggerManager.dispose();
    if (processManager) processManager.stop();
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
