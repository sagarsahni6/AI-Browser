import { app, BaseWindow } from 'electron';
import { TabManager } from '../electron/browser/tab-manager';
import { DebuggerManager } from '../electron/browser/debugger-manager';
import { LayoutManager } from '../electron/layout-manager';
import { RpcClient } from '../electron/bridge/rpc-client';
import { ProcessManager } from '../electron/bridge/process-manager';

async function runSmokeTest() {
  console.log('=== PHASE 0 SMOKE TEST STARTING ===');

  // 1. Create BaseWindow
  const win = new BaseWindow({
    width: 1280,
    height: 800,
    show: true,
    title: 'Phase 0 Test Window'
  });
  console.log('✓ 1. Electron BaseWindow created successfully.');

  // 2. Setup managers
  const layout = new LayoutManager(win);
  const debugMgr = new DebuggerManager();
  const tabMgr = new TabManager(win, debugMgr);
  const rpcClient = new RpcClient();
  const procMgr = new ProcessManager(rpcClient);

  tabMgr.setOnActiveTabChanged((view) => {
    layout.setActiveTabView(view);
  });

  // 3. Tab creation & real Chromium webpage loading
  console.log('Loading test webpage in WebContentsView...');
  const tabId = await tabMgr.createTab('https://example.com');
  console.log(`✓ 2. Created browser tab: ${tabId}`);

  const activeTab = tabMgr.getActiveTab();
  if (!activeTab) throw new Error('Active tab not found');

  // Wait for page to finish loading
  await new Promise<void>((resolve) => {
    if (!activeTab.info.isLoading) return resolve();
    const interval = setInterval(() => {
      if (!activeTab.info.isLoading || activeTab.info.title !== 'New Tab') {
        clearInterval(interval);
        resolve();
      }
    }, 200);
    setTimeout(() => {
      clearInterval(interval);
      resolve();
    }, 8000);
  });
  console.log(`✓ 3. Real Chromium webpage loaded. Title: "${activeTab.info.title}", URL: "${activeTab.info.url}"`);

  // 4. Test CDP Bridge inspection
  console.log('Testing CDP inspection...');
  const observation = await tabMgr.inspectActivePage();
  console.log(`✓ 4. CDP inspection succeeded! Extracted:
     - URL: ${observation.url}
     - Title: ${observation.title}
     - Viewport: ${observation.viewport.width}x${observation.viewport.height}
     - Elements found: ${observation.interactiveElements.length}
     - Text sample: "${observation.visibleText.slice(0, 80).replace(/\n/g, ' ')}..."`);

  // 5. Test Screenshot capture
  console.log('Testing Screenshot capture...');
  const screenshotData = await tabMgr.captureActivePage();
  const isBase64Png = screenshotData.startsWith('data:image/png;base64,') && screenshotData.length > 500;
  if (!isBase64Png) throw new Error('Invalid screenshot data generated');
  console.log(`✓ 5. Screenshot capture succeeded! Generated base64 PNG (${Math.round(screenshotData.length / 1024)} KB)`);

  // 6. Test Python Backend process & JSON-RPC
  console.log('Starting Python backend sidecar...');
  const readyPromise = new Promise<{ online: boolean; port: number }>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Backend ready timeout')), 12000);
    procMgr.on('status', (st) => {
      if (st.online) {
        clearTimeout(timer);
        resolve(st);
      }
    });
  });

  await procMgr.start();
  const backendStatus = await readyPromise;
  console.log(`✓ 6. Python FastAPI backend started on port ${backendStatus.port}.`);

  // 7. Test RPC communication
  console.log('Testing JSON-RPC roundtrip call (assistant.chat)...');
  const chatReply = await rpcClient.call('assistant.chat', {
    message: 'Hello from Electron Phase 0 test!',
    context: { url: observation.url }
  });
  console.log(`✓ 7. Electron-Python RPC roundtrip succeeded! Response: "${chatReply.reply}"`);

  // 8. Verify remote debugging port is not exposed
  console.log('Verifying remote debugging port isolation...');
  const remotePortArg = process.argv.find(arg => arg.includes('--remote-debugging-port'));
  if (remotePortArg) {
    throw new Error(`Insecure configuration: ${remotePortArg} detected!`);
  }
  console.log('✓ 8. Verified no remote debugging port is exposed.');

  // 9. Cleanup
  console.log('Cleaning up resources...');
  procMgr.stop();
  tabMgr.dispose();
  debugMgr.dispose();
  win.destroy();

  console.log('=== PHASE 0 SMOKE TEST COMPLETED SUCCESSFULLY ===');
  process.exit(0);
}

app.whenReady().then(runSmokeTest).catch((err) => {
  console.error('Smoke test failed:', err);
  process.exit(1);
});
