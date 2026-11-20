import { WebContentsView } from 'electron';
import path from 'path';
import { pathToFileURL } from 'url';

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

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    view.webContents.loadURL(`${devUrl}?panel=${panelName}`);
  } else {
    const indexPath = path.resolve(__dirname, '../renderer/index.html');
    const fileUrl = `${pathToFileURL(indexPath).toString()}?panel=${panelName}`;
    view.webContents.loadURL(fileUrl);
  }

  return view;
}
