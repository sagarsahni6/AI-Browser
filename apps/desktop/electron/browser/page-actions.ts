import type { CdpClient } from './cdp-client';

export class PageActions {
  private cdp: CdpClient;

  constructor(cdp: CdpClient) {
    this.cdp = cdp;
  }

  public async click(x: number, y: number): Promise<boolean> {
    await this.cdp.attach();

    // Mouse move -> press -> release
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
    // 1. Click to focus
    await this.click(x, y);

    // 2. Select all existing text (Ctrl+A / Cmd+A)
    await this.cdp.sendCommand('Input.dispatchKeyEvent', {
      type: 'keyDown',
      commands: ['selectAll']
    });

    // 3. Insert new text
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
}
