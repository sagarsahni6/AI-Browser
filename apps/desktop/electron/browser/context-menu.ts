import { Menu, MenuItem, type WebContents } from 'electron';

export function attachContextMenu(
  wc: WebContents,
  callbacks: {
    onBookmarkPage?: (url: string, title: string) => void;
    onAskAI?: (selectedText: string) => void;
  }
) {
  wc.on('context-menu', (_event, params) => {
    const menu = new Menu();

    // Navigation items
    const hasNavHistory = Boolean(wc.navigationHistory);
    menu.append(new MenuItem({
      label: 'Back',
      enabled: hasNavHistory ? wc.navigationHistory.canGoBack() : wc.canGoBack(),
      click: () => (hasNavHistory ? wc.navigationHistory.goBack() : wc.goBack()),
    }));

    menu.append(new MenuItem({
      label: 'Forward',
      enabled: hasNavHistory ? wc.navigationHistory.canGoForward() : wc.canGoForward(),
      click: () => (hasNavHistory ? wc.navigationHistory.goForward() : wc.goForward()),
    }));

    menu.append(new MenuItem({
      label: 'Reload',
      click: () => wc.reload(),
    }));

    menu.append(new MenuItem({ type: 'separator' }));

    // Selection / Edit items
    if (params.selectionText) {
      menu.append(new MenuItem({
        label: `Ask AI about "${params.selectionText.slice(0, 24)}..."`,
        click: () => callbacks.onAskAI?.(params.selectionText),
      }));

      menu.append(new MenuItem({ type: 'separator' }));

      menu.append(new MenuItem({
        label: 'Copy',
        role: 'copy',
      }));
    }

    if (params.isEditable) {
      menu.append(new MenuItem({ label: 'Cut', role: 'cut' }));
      menu.append(new MenuItem({ label: 'Paste', role: 'paste' }));
      menu.append(new MenuItem({ label: 'Select All', role: 'selectAll' }));
      menu.append(new MenuItem({ type: 'separator' }));
    }

    menu.append(new MenuItem({
      label: 'Bookmark Page',
      click: () => callbacks.onBookmarkPage?.(wc.getURL(), wc.getTitle()),
    }));

    menu.append(new MenuItem({ type: 'separator' }));

    menu.append(new MenuItem({
      label: 'Inspect Element',
      click: () => {
        wc.inspectElement(params.x, params.y);
      },
    }));

    menu.popup();
  });
}
