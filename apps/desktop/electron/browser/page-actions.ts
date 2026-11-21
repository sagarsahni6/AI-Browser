import type { CdpClient } from './cdp-client';
import type { WebContents } from 'electron';

export class PageActions {
  private cdp: CdpClient;
  private webContents?: WebContents;

  constructor(cdp: CdpClient, webContents?: WebContents) {
    this.cdp = cdp;
    this.webContents = webContents;
  }

  public async click(x: number, y: number): Promise<boolean> {
    await this.cdp.attach();

    await this.cdp.sendCommand('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x,
      y
    });

    await this.cdp.sendCommand('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x,
      y,
      button: 'left',
      clickCount: 1
    });

    await this.cdp.sendCommand('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x,
      y,
      button: 'left',
      clickCount: 1
    });

    return true;
  }

  public async typeText(text: string): Promise<boolean> {
    await this.cdp.attach();
    await this.cdp.sendCommand('Input.insertText', { text });
    return true;
  }

  public async fillInput(x: number, y: number, text: string): Promise<boolean> {
    await this.click(x, y);

    await this.cdp.sendCommand('Input.dispatchKeyEvent', {
      type: 'keyDown',
      commands: ['selectAll']
    });

    await this.typeText(text);
    return true;
  }

  public async scrollPage(deltaX: number, deltaY: number): Promise<boolean> {
    await this.cdp.attach();
    await this.cdp.sendCommand('Input.dispatchMouseEvent', {
      type: 'mouseWheel',
      x: 400,
      y: 400,
      deltaX,
      deltaY
    });
    return true;
  }

  public async pressKey(key: string): Promise<boolean> {
    await this.cdp.attach();
    await this.cdp.sendCommand('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key
    });
    await this.cdp.sendCommand('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key
    });
    return true;
  }

  /**
   * DOM-first selector clicking: finds element, scrolls into view, computes viewport coordinates,
   * dispatches trusted CDP mouse events, with a fallback to direct DOM click.
   */
  public async clickSelector(selector: string): Promise<{ success: boolean; x?: number; y?: number; error?: string }> {
    if (!this.webContents || this.webContents.isDestroyed()) {
      return { success: false, error: 'WebContents unavailable' };
    }

    try {
      const coordScript = `
        (() => {
          let el = null;
          const sel = ${JSON.stringify(selector)};
          if (sel.startsWith('text=')) {
            const searchText = sel.slice(5).trim().toLowerCase();
            const all = Array.from(document.querySelectorAll('button, a, input[type="submit"], [role="button"], span, p, div'));
            el = all.find(e => (e.innerText || e.textContent || '').trim().toLowerCase() === searchText)
              || all.find(e => (e.innerText || e.textContent || '').trim().toLowerCase().includes(searchText));
          } else {
            el = document.querySelector(sel);
          }

          if (!el) return { error: 'Element not found for selector: ' + sel };

          el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });
          const rect = el.getBoundingClientRect();
          if (rect.width === 0 && rect.height === 0) {
            return { error: 'Element is hidden or has 0 dimensions' };
          }

          return {
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2)
          };
        })()
      `;

      const coords = await this.webContents.executeJavaScript(coordScript);
      if (coords?.error) {
        return { success: false, error: coords.error };
      }

      const { x, y } = coords;
      await this.click(x, y);
      return { success: true, x, y };
    } catch (err: any) {
      // Fallback: direct DOM click
      try {
        await this.webContents.executeJavaScript(`
          (() => {
            const el = document.querySelector(${JSON.stringify(selector)});
            if (el) { el.click(); return true; }
            return false;
          })()
        `);
        return { success: true };
      } catch (fallbackErr: any) {
        return { success: false, error: err.message || String(err) };
      }
    }
  }

  /**
   * DOM-first selector filling: focuses element, clears, and inputs text.
   * Also triggers modern framework synthetic events (input, change).
   */
  public async fillSelector(selector: string, text: string): Promise<{ success: boolean; textLength: number; error?: string }> {
    if (!this.webContents || this.webContents.isDestroyed()) {
      return { success: false, textLength: 0, error: 'WebContents unavailable' };
    }

    try {
      const fillScript = `
        (() => {
          const sel = ${JSON.stringify(selector)};
          const el = document.querySelector(sel);
          if (!el) return { error: 'Input element not found for selector: ' + sel };

          el.scrollIntoView({ behavior: 'instant', block: 'center' });
          el.focus();

          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
            || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;

          if (nativeInputValueSetter) {
            nativeInputValueSetter.call(el, ${JSON.stringify(text)});
          } else {
            el.value = ${JSON.stringify(text)};
          }

          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));

          const rect = el.getBoundingClientRect();
          return {
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2)
          };
        })()
      `;

      const res = await this.webContents.executeJavaScript(fillScript);
      if (res?.error) {
        return { success: false, textLength: 0, error: res.error };
      }

      return { success: true, textLength: text.length };
    } catch (err: any) {
      return { success: false, textLength: 0, error: err.message || String(err) };
    }
  }

  /**
   * Waits until an element matching the selector appears in the DOM and is visible.
   */
  public async waitForSelector(selector: string, timeoutMs: number = 5000): Promise<{ found: boolean; elapsedMs: number }> {
    if (!this.webContents || this.webContents.isDestroyed()) {
      return { found: false, elapsedMs: 0 };
    }

    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const checkScript = `
        (() => {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return (rect.width > 0 && rect.height > 0) || el.offsetParent !== null;
        })()
      `;
      try {
        const found = await this.webContents.executeJavaScript(checkScript);
        if (found) {
          return { found: true, elapsedMs: Date.now() - start };
        }
      } catch (e) {
        // Continue waiting
      }
      await new Promise(r => setTimeout(r, 200));
    }

    return { found: false, elapsedMs: Date.now() - start };
  }

  /**
   * Scans the active page for HTML forms and form-like input containers,
   * extracting input labels, types, names, and current values.
   */
  public async detectForms(): Promise<any[]> {
    if (!this.webContents || this.webContents.isDestroyed()) return [];

    const script = `
      (() => {
        const forms = [];
        const formElements = Array.from(document.querySelectorAll('form'));

        const getFields = (container) => {
          return Array.from(container.querySelectorAll('input, select, textarea')).map((el, idx) => {
            let label = '';
            if (el.id) {
              const labelEl = document.querySelector('label[for="' + el.id + '"]');
              if (labelEl) label = labelEl.innerText.trim();
            }
            if (!label && el.closest('label')) {
              label = el.closest('label').innerText.trim();
            }
            if (!label) {
              label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || '';
            }

            return {
              id: el.id || ('input-' + idx),
              name: el.name || '',
              type: el.type || el.tagName.toLowerCase(),
              label: label,
              placeholder: el.placeholder || '',
              value: el.type === 'password' ? '***' : (el.value || ''),
              required: el.required || false
            };
          });
        };

        if (formElements.length > 0) {
          formElements.forEach((f, idx) => {
            forms.push({
              id: f.id || ('form-' + idx),
              action: f.action || '',
              method: (f.method || 'GET').toUpperCase(),
              fields: getFields(f)
            });
          });
        } else {
          // Check for orphan inputs
          const orphanFields = getFields(document.body);
          if (orphanFields.length > 0) {
            forms.push({
              id: 'implicit-form-0',
              action: window.location.href,
              method: 'POST',
              fields: orphanFields
            });
          }
        }

        return forms;
      })()
    `;

    try {
      return await this.webContents.executeJavaScript(script);
    } catch (e) {
      return [];
    }
  }

  /**
   * Retrieves the full accessibility tree from Chromium via CDP.
   */
  public async getAccessibilityTree(): Promise<any> {
    await this.cdp.attach();
    try {
      const axTree = await this.cdp.sendCommand('Accessibility.getFullAXTree', { depth: 4 });
      return axTree?.nodes || [];
    } catch (e: any) {
      return { error: e.message || String(e) };
    }
  }
}
