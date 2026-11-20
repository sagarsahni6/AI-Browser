import type { WebContents } from 'electron';

export interface ShortcutHandlers {
  onNewTab: () => void;
  onCloseTab: () => void;
  onReload: () => void;
  onRestoreClosedTab: () => void;
  onGoBack: () => void;
  onGoForward: () => void;
  onNextTab: () => void;
  onPrevTab: () => void;
  onToggleSidebar: () => void;
  onToggleAssistant: () => void;
  onOpenCommandPalette?: () => void;
}

export function registerShortcuts(wc: WebContents, handlers: ShortcutHandlers) {
  wc.on('before-input-event', (_event, input) => {
    if (input.type !== 'keyDown') return;

    const isCtrlOrCmd = process.platform === 'darwin' ? input.meta : input.control;

    // Ctrl+T: New Tab
    if (isCtrlOrCmd && !input.shift && input.key.toLowerCase() === 't') {
      _event.preventDefault();
      handlers.onNewTab();
      return;
    }

    // Ctrl+Shift+T: Restore closed tab
    if (isCtrlOrCmd && input.shift && input.key.toLowerCase() === 't') {
      _event.preventDefault();
      handlers.onRestoreClosedTab();
      return;
    }

    // Ctrl+W: Close Tab
    if (isCtrlOrCmd && !input.shift && input.key.toLowerCase() === 'w') {
      _event.preventDefault();
      handlers.onCloseTab();
      return;
    }

    // Ctrl+R or F5: Reload
    if ((isCtrlOrCmd && input.key.toLowerCase() === 'r') || input.key === 'F5') {
      _event.preventDefault();
      handlers.onReload();
      return;
    }

    // Alt+Left: Back
    if (input.alt && input.key === 'ArrowLeft') {
      _event.preventDefault();
      handlers.onGoBack();
      return;
    }

    // Alt+Right: Forward
    if (input.alt && input.key === 'ArrowRight') {
      _event.preventDefault();
      handlers.onGoForward();
      return;
    }

    // Ctrl+Tab / Ctrl+Shift+Tab
    if (isCtrlOrCmd && input.key === 'Tab') {
      _event.preventDefault();
      if (input.shift) {
        handlers.onPrevTab();
      } else {
        handlers.onNextTab();
      }
      return;
    }

    // Ctrl+H or Ctrl+B or Ctrl+J: Sidebar
    if (isCtrlOrCmd && ['h', 'b', 'j'].includes(input.key.toLowerCase())) {
      _event.preventDefault();
      handlers.onToggleSidebar();
      return;
    }

    // Ctrl+Shift+A or Ctrl+I: Assistant
    if (isCtrlOrCmd && (input.key.toLowerCase() === 'i' || (input.shift && input.key.toLowerCase() === 'a'))) {
      _event.preventDefault();
      handlers.onToggleAssistant();
      return;
    }

    // Ctrl+K: Command Palette
    if (isCtrlOrCmd && input.key.toLowerCase() === 'k') {
      _event.preventDefault();
      handlers.onOpenCommandPalette?.();
      return;
    }
  });
}
