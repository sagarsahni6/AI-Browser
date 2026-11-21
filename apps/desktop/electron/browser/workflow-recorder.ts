import type { WebContents } from 'electron';

export interface RecordedStep {
  step: number;
  action: string;
  description: string;
  parameters: Record<string, any>;
}

export class WorkflowRecorder {
  private static instance: WorkflowRecorder;
  private isRecording = false;
  private currentWebContents: WebContents | null = null;
  private recordedSteps: RecordedStep[] = [];
  private navListener: ((event: any, url: string) => void) | null = null;

  public static getInstance(): WorkflowRecorder {
    if (!WorkflowRecorder.instance) {
      WorkflowRecorder.instance = new WorkflowRecorder();
    }
    return WorkflowRecorder.instance;
  }

  public getIsRecording(): boolean {
    return this.isRecording;
  }

  public async startRecording(webContents: WebContents): Promise<{ status: string }> {
    this.isRecording = true;
    this.currentWebContents = webContents;
    this.recordedSteps = [];

    // 1. Record initial page URL as step 1
    const currentUrl = webContents.getURL();
    if (currentUrl && !currentUrl.startsWith('about:')) {
      this.recordedSteps.push({
        step: 1,
        action: 'navigate',
        description: `Navigate to ${currentUrl}`,
        parameters: { url: currentUrl }
      });
    }

    // 2. Attach navigation listener
    this.navListener = (_event, url) => {
      if (this.isRecording && url && !url.startsWith('about:') && !url.startsWith('data:')) {
        const lastStep = this.recordedSteps[this.recordedSteps.length - 1];
        if (!lastStep || lastStep.action !== 'navigate' || lastStep.parameters.url !== url) {
          this.recordedSteps.push({
            step: this.recordedSteps.length + 1,
            action: 'navigate',
            description: `Navigate to ${url}`,
            parameters: { url }
          });
        }
      }
    };
    webContents.on('did-navigate', this.navListener);

    // 3. Inject in-page capture script
    const injectScript = `
      (() => {
        if (window.__workflowRecorderActive) return;
        window.__workflowRecorderActive = true;
        window.__recordedActions = [];

        function getSelector(el) {
          if (!el || el === document.body) return 'body';
          if (el.id) return '#' + el.id;
          if (el.getAttribute('name')) return el.tagName.toLowerCase() + '[name="' + el.getAttribute('name') + '"]';
          if (el.getAttribute('aria-label')) return el.tagName.toLowerCase() + '[aria-label="' + el.getAttribute('aria-label') + '"]';
          if (el.classList && el.classList.length > 0) {
            const cls = Array.from(el.classList).filter(c => !c.includes(':')).slice(0, 2).join('.');
            if (cls) return el.tagName.toLowerCase() + '.' + cls;
          }
          const text = (el.innerText || el.textContent || '').trim();
          if (text && text.length < 25 && ['BUTTON', 'A'].includes(el.tagName)) {
            return 'text=' + text;
          }
          return el.tagName.toLowerCase();
        }

        document.addEventListener('click', (e) => {
          if (!window.__workflowRecorderActive) return;
          const target = e.target;
          if (!target) return;
          const selector = getSelector(target);
          window.__recordedActions.push({
            type: 'click',
            selector: selector,
            tag: target.tagName.toLowerCase(),
            text: (target.innerText || '').slice(0, 30)
          });
        }, true);

        document.addEventListener('change', (e) => {
          if (!window.__workflowRecorderActive) return;
          const target = e.target;
          if (!target || !['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return;
          const selector = getSelector(target);
          window.__recordedActions.push({
            type: 'fill',
            selector: selector,
            value: target.value || ''
          });
        }, true);
      })()
    `;

    try {
      await webContents.executeJavaScript(injectScript);
    } catch (e) {
      console.warn('[WorkflowRecorder] Failed to inject recording script:', e);
    }

    return { status: 'recording' };
  }

  public async stopRecording(): Promise<RecordedStep[]> {
    if (!this.isRecording) return this.recordedSteps;
    this.isRecording = false;

    if (this.currentWebContents && !this.currentWebContents.isDestroyed()) {
      if (this.navListener) {
        this.currentWebContents.removeListener('did-navigate', this.navListener);
        this.navListener = null;
      }

      try {
        const harvested = await this.currentWebContents.executeJavaScript(`
          (() => {
            window.__workflowRecorderActive = false;
            const acts = window.__recordedActions || [];
            window.__recordedActions = [];
            return acts;
          })()
        `);

        if (Array.isArray(harvested)) {
          for (const item of harvested) {
            if (item.type === 'click') {
              this.recordedSteps.push({
                step: this.recordedSteps.length + 1,
                action: 'click_selector',
                description: `Click ${item.selector}`,
                parameters: { selector: item.selector }
              });
            } else if (item.type === 'fill') {
              this.recordedSteps.push({
                step: this.recordedSteps.length + 1,
                action: 'fill_selector',
                description: `Type into ${item.selector}`,
                parameters: { selector: item.selector, text: item.value }
              });
            }
          }
        }
      } catch (e) {
        console.warn('[WorkflowRecorder] Error harvesting recorded actions:', e);
      }
    }

    this.currentWebContents = null;
    return this.recordedSteps;
  }
}
