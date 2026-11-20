import { WebContentsView } from 'electron';
import path from 'path';
import { pathToFileURL } from 'url';

export function getPanelUrl(panelName: string): string {
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    return `${devUrl}?panel=${panelName}`;
  } else {
    const indexPath = path.resolve(__dirname, '../renderer/index.html');
    return `${pathToFileURL(indexPath).toString()}?panel=${panelName}`;
  }
}

export function createPanelView(panelName: 'toolbar' | 'sidebar' | 'assistant'): WebContentsView {
  const preloadPath = path.resolve(__dirname, 'preload.js');

  const view = new WebContentsView({
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    }
  });

  view.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  view.webContents.loadURL(getPanelUrl(panelName));

  return view;
}
