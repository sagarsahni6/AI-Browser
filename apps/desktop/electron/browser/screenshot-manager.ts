import type { WebContents } from 'electron';
import type { CdpClient } from './cdp-client';

export class ScreenshotManager {
  public static async capture(webContents: WebContents, cdp?: CdpClient): Promise<string> {
    if (webContents.isDestroyed()) {
      throw new Error('WebContents is destroyed');
    }

    // 1. Try CDP Page.captureScreenshot first if CDP is available
    if (cdp) {
      try {
        await cdp.attach();
        await cdp.sendCommand('Page.enable');
        const res: any = await cdp.sendCommand('Page.captureScreenshot', { format: 'png' });
        if (res?.data) {
          return `data:image/png;base64,${res.data}`;
        }
      } catch (err: any) {
        console.warn('CDP screenshot failed, trying capturePage fallback:', err?.message);
      }
    }

    // 2. Try native capturePage
    try {
      const nativeImage = await webContents.capturePage();
      const dataUrl = nativeImage.toDataURL();
      if (dataUrl && dataUrl.length > 100) {
        return dataUrl;
      }
    } catch (err: any) {
      console.warn('Native capturePage failed:', err?.message);
    }

    throw new Error('Unable to capture screenshot through both native and CDP pipelines');
  }
}
