import type { WebContents } from 'electron';
import type { PageObservation, InteractiveElement } from '@ai-browser/shared';
import { CdpClient } from './cdp-client';
import { AccessibilityReader, type AccessibilityNode } from './accessibility-reader';

export interface ExtendedPageObservation extends PageObservation {
  accessibilityTree?: AccessibilityNode[];
}

export class PageObserver {
  private cdp: CdpClient;
  private webContents: WebContents;
  private axReader: AccessibilityReader;

  constructor(webContents: WebContents, cdp: CdpClient) {
    this.webContents = webContents;
    this.cdp = cdp;
    this.axReader = new AccessibilityReader(cdp);
  }

  public async observe(tabId: string): Promise<ExtendedPageObservation> {
    await this.cdp.attach();
    await this.cdp.sendCommand('Runtime.enable');
    await this.cdp.sendCommand('DOM.enable');

    // Safe extraction script: ignores input[type=password] and sensitive credential fields
    const extractionScript = `
      (() => {
        // Redact any password fields from extraction
        const passwords = document.querySelectorAll('input[type="password"]');
        passwords.forEach(el => el.setAttribute('data-sensitive', 'true'));

        const text = (document.body ? document.body.innerText : '') || '';
        const viewport = {
          width: window.innerWidth || 1280,
          height: window.innerHeight || 800
        };

        const metaDescEl = document.querySelector('meta[name="description"]');
        const metaDescription = metaDescEl ? metaDescEl.getAttribute('content') || undefined : undefined;

        const getDeterministicSelector = (el) => {
          // Priority 1: #id
          if (el.id && typeof el.id === 'string' && el.id.trim()) {
            const cleanId = el.id.trim();
            return '#' + (window.CSS && CSS.escape ? CSS.escape(cleanId) : cleanId);
          }
          // Priority 2: [data-testid]
          const testId = el.getAttribute('data-testid');
          if (testId) {
            return '[data-testid="' + testId + '"]';
          }
          // Priority 3: [name]
          const nameAttr = el.getAttribute('name');
          if (nameAttr) {
            return '[name="' + nameAttr + '"]';
          }
          // Priority 4: [aria-label]
          const ariaLabel = el.getAttribute('aria-label');
          if (ariaLabel) {
            return '[aria-label="' + ariaLabel + '"]';
          }
          // Priority 5: text=...
          const rawText = (el.innerText || (el instanceof HTMLInputElement ? el.value : '') || '').trim();
          if (rawText && rawText.length <= 50) {
            return 'text=' + rawText.replace(/\\s+/g, ' ');
          }
          // Priority 6: tag:nth-of-type(n)
          const tag = el.tagName.toLowerCase();
          const parent = el.parentElement;
          if (!parent) return tag;
          const siblings = Array.from(parent.children).filter(c => c.tagName.toLowerCase() === tag);
          const index = siblings.indexOf(el) + 1;
          return tag + ':nth-of-type(' + (index > 0 ? index : 1) + ')';
        };

        const elements = [];
        const selector = 'button, a, input:not([type="password"]), textarea, select, [role="button"], [role="link"], [role="checkbox"]';
        const nodes = Array.from(document.querySelectorAll(selector));

        nodes.slice(0, 100).forEach((el, index) => {
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            const isDisabled = Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true');
            elements.push({
              id: 'el-' + index,
              selector: getDeterministicSelector(el),
              tagName: el.tagName.toLowerCase(),
              role: el.getAttribute('role') || undefined,
              label: el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') || undefined,
              text: (el.innerText || (el instanceof HTMLInputElement ? el.value : '') || '').slice(0, 100).trim(),
              disabled: isDisabled,
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
          metaDescription,
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

    // Get accessibility tree
    const axTree = await this.axReader.getTree();

    const sanitizeText = (str?: string): string => {
      if (!str) return '';
      return typeof (str as any).toWellFormed === 'function'
        ? (str as any).toWellFormed()
        : str.replace(/[\uD800-\uDFFF]/g, '');
    };

    return {
      tabId,
      url: sanitizeText(val.url),
      title: sanitizeText(val.title),
      metaDescription: val.metaDescription ? sanitizeText(val.metaDescription) : undefined,
      viewport: val.viewport,
      visibleText: sanitizeText(val.visibleText),
      interactiveElements: val.interactiveElements,
      accessibilityTree: axTree
    };
  }
}
