import { app, BaseWindow } from 'electron';
import { createPanelView } from './panels/panel-factory';
import { LayoutManager } from './layout-manager';
import { TabManager } from './browser/tab-manager';
import { DebuggerManager } from './browser/debugger-manager';
import { RpcClient } from './bridge/rpc-client';
import { ProcessManager } from './bridge/process-manager';
import { setupIpcHandlers } from './bridge/ipc-handlers';

let mainWindow: BaseWindow | null = null;
let tabManager: TabManager | null = null;
let debuggerManager: DebuggerManager | null = null;
let processManager: ProcessManager | null = null;

async function createWindow() {
  mainWindow = new BaseWindow({
    width: 1360,
    height: 860,
    minWidth: 840,
    minHeight: 600,
    show: false,
    title: 'AI Browser',
    backgroundColor: '#0d0f12',
  });

  const layoutManager = new LayoutManager(mainWindow);
  debuggerManager = new DebuggerManager();
  tabManager = new TabManager(mainWindow, debuggerManager);
  const rpcClient = new RpcClient();
  processManager = new ProcessManager(rpcClient);

  // 1. Create panel views
  const toolbarView = createPanelView('toolbar');
  const sidebarView = createPanelView('sidebar');
  const assistantView = createPanelView('assistant');

  // Add panel views to BaseWindow contentView
  mainWindow.contentView.addChildView(toolbarView);
  mainWindow.contentView.addChildView(sidebarView);
  mainWindow.contentView.addChildView(assistantView);

  layoutManager.setViews({
    toolbar: toolbarView,
    sidebar: sidebarView,
    assistant: assistantView,
  });

  tabManager.setOnActiveTabChanged((tabView) => {
    layoutManager.setActiveTabView(tabView);
  });

  // Setup IPC Handlers
  setupIpcHandlers({
    tabManager,
    layoutManager,
    processManager,
    rpcClient,
    panelViews: [toolbarView, sidebarView, assistantView],
  });

  // Listen to window resize to recalculate bounds
  mainWindow.on('resize', () => {
    layoutManager.updateBounds();
  });

  mainWindow.on('maximize', () => {
    layoutManager.updateBounds();
  });

  mainWindow.on('unmaximize', () => {
    layoutManager.updateBounds();
  });

  // Create initial tab
  await tabManager.createTab('https://example.com');

  // Show window once ready
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
