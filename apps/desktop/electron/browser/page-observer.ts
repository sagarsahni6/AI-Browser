import type { WebContents } from 'electron';
import type { PageObservation, InteractiveElement } from '@ai-browser/shared';
import { CdpClient } from './cdp-client';

export class PageObserver {
  private cdp: CdpClient;
  private webContents: WebContents;

  constructor(webContents: WebContents, cdp: CdpClient) {
    this.webContents = webContents;
    this.cdp = cdp;
  }

  public async observe(tabId: string): Promise<PageObservation> {
    await this.cdp.attach();

    // Enable Runtime & DOM
    await this.cdp.sendCommand('Runtime.enable');
    await this.cdp.sendCommand('DOM.enable');

    // Safe extraction script inside the page context
    const extractionScript = `
      (() => {
        const text = (document.body ? document.body.innerText : '') || '';
        const viewport = {
          width: window.innerWidth || 1280,
          height: window.innerHeight || 800
        };

        const elements = [];
        const selector = 'button, a, input, textarea, select, [role="button"], [role="link"]';
        const nodes = Array.from(document.querySelectorAll(selector));

        nodes.slice(0, 100).forEach((el, index) => {
          const rect = el.getBoundingClientRect();
          // Filter out completely hidden elements
          if (rect.width > 0 && rect.height > 0) {
            elements.push({
              id: 'el-' + index,
              tagName: el.tagName.toLowerCase(),
              role: el.getAttribute('role') || undefined,
              label: el.getAttribute('aria-label') || el.getAttribute('placeholder') || undefined,
              text: (el.innerText || (el instanceof HTMLInputElement ? el.value : '') || '').slice(0, 100).trim(),
              bounds: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
              }
            });
          }
        });

        return {
          url: window.location.href,
          title: document.title,
          viewport,
          visibleText: text.slice(0, 8000),
          interactiveElements: elements
        };
      })()
    `;

    const evalResult: any = await this.cdp.sendCommand('Runtime.evaluate', {
      expression: extractionScript,
      returnByValue: true
    });

    const val = evalResult?.result?.value || {
      url: this.webContents.getURL(),
      title: this.webContents.getTitle(),
      viewport: { width: 1280, height: 800 },
      visibleText: '',
      interactiveElements: []
    };

    return {
      tabId,
      url: val.url,
      title: val.title,
      viewport: val.viewport,
      visibleText: val.visibleText,
      interactiveElements: val.interactiveElements
    };
  }
}
